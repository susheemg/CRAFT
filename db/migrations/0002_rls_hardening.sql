-- 0002_rls_hardening.sql
--
-- Two defects found by the test suite, both of the same kind: a control that
-- appeared to be on but did not engage.
--
-- 1. ENABLE ROW LEVEL SECURITY does not apply to the table's owner. Because the
--    application connects as the owner in most deployments — including Render's
--    managed Postgres, where the provisioned user owns everything — the tenant
--    policies were never consulted. FORCE ROW LEVEL SECURITY closes that.
--
-- 2. The original policy treated an unset app.tenant_id as "match everything".
--    That fails open: any code path that forgot to bind the session would read
--    across every tenant. It is now fail-closed, with a single explicit,
--    deliberately-named escape hatch (app.bypass_rls) that only migrations and
--    the seeder set.
--
-- 3. The append-only trigger fires on INSERT/UPDATE/DELETE. TRUNCATE is a
--    separate event and was not covered, so the log could be emptied wholesale
--    while individual rows were protected. A statement-level trigger closes it.

-- ---------------------------------------------------------------------
-- 1. Force RLS and replace the policies
-- ---------------------------------------------------------------------
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN
        SELECT c.table_schema, c.table_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema AND t.table_name = c.table_name
        WHERE c.column_name = 'tenant_id'
          AND t.table_type = 'BASE TABLE'
          AND c.table_schema IN ('core','domain','compliance','config','integ','iam')
    LOOP
        EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',
                       r.table_schema, r.table_name);
        -- Without FORCE, the owner bypasses every policy below.
        EXECUTE format('ALTER TABLE %I.%I FORCE ROW LEVEL SECURITY',
                       r.table_schema, r.table_name);

        EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I.%I',
                       r.table_schema, r.table_name);

        -- USING governs what can be read and modified; WITH CHECK governs what
        -- can be written. Both are needed: without WITH CHECK a session could
        -- insert a row stamped with someone else's tenant_id.
        EXECUTE format($f$
            CREATE POLICY tenant_isolation ON %I.%I
            USING (
                tenant_id::text = current_setting('app.tenant_id', true)
                OR current_setting('app.bypass_rls', true) = 'on'
            )
            WITH CHECK (
                tenant_id::text = current_setting('app.tenant_id', true)
                OR current_setting('app.bypass_rls', true) = 'on'
            )
        $f$, r.table_schema, r.table_name);
    END LOOP;
END;
$$;

-- The audit log is readable within a tenant but never updatable or deletable;
-- the trigger enforces that regardless of policy, and this keeps the read side
-- consistent with every other tenant-scoped table.
ALTER TABLE audit.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit.audit_log FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON audit.audit_log;
CREATE POLICY tenant_isolation ON audit.audit_log
    USING (
        tenant_id::text = current_setting('app.tenant_id', true)
        OR current_setting('app.bypass_rls', true) = 'on'
    )
    WITH CHECK (
        tenant_id::text = current_setting('app.tenant_id', true)
        OR current_setting('app.bypass_rls', true) = 'on'
    );

-- ---------------------------------------------------------------------
-- 2. Block TRUNCATE on the append-only tables
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION audit.refuse_truncate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Table %.% is append-only; TRUNCATE is not permitted.',
        TG_TABLE_SCHEMA, TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege';
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_log_no_truncate ON audit.audit_log;
CREATE TRIGGER trg_audit_log_no_truncate
    BEFORE TRUNCATE ON audit.audit_log
    FOR EACH STATEMENT
    EXECUTE FUNCTION audit.refuse_truncate();

DROP TRIGGER IF EXISTS trg_evidence_no_truncate ON core.evidence_record;
CREATE TRIGGER trg_evidence_no_truncate
    BEFORE TRUNCATE ON core.evidence_record
    FOR EACH STATEMENT
    EXECUTE FUNCTION audit.refuse_truncate();

-- ---------------------------------------------------------------------
-- 3. Evidence records are append-only too
--
-- Evidence that can be edited after the fact is not evidence. Corrections are
-- made by superseding a record, which leaves both versions in place.
-- ---------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_evidence_immutable ON core.evidence_record;
CREATE TRIGGER trg_evidence_immutable
    BEFORE UPDATE OR DELETE ON core.evidence_record
    FOR EACH ROW
    EXECUTE FUNCTION audit.refuse_mutation();

COMMENT ON POLICY tenant_isolation ON audit.audit_log IS
    'Fail-closed tenant isolation. An unbound session reads nothing. '
    'app.bypass_rls is set only by migrations and the seeder.';
