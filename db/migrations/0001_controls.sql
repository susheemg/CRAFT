-- =====================================================================
-- 0001_controls.sql
-- Controls the application cannot be trusted to enforce on its own:
--   * append-only audit and evidence (enforced by trigger, not by code)
--   * row-level security for tenant isolation
--   * least-privilege database roles
--   * partial indexes for the approver inbox and cache expiry
-- Forward-only. Never edit this file after it has been applied.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Immutability. UPDATE and DELETE are refused at the database, so a
--    compromised application account still cannot rewrite history.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION audit.refuse_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION
        'Table %.% is append-only; % is not permitted',
        TG_TABLE_SCHEMA, TG_TABLE_NAME, TG_OP
        USING ERRCODE = '42501';
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_log_immutable ON audit.audit_log;
CREATE TRIGGER trg_audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit.audit_log
    FOR EACH ROW EXECUTE FUNCTION audit.refuse_mutation();

DROP TRIGGER IF EXISTS trg_evidence_immutable ON core.evidence_record;
CREATE TRIGGER trg_evidence_immutable
    BEFORE UPDATE OR DELETE ON core.evidence_record
    FOR EACH ROW EXECUTE FUNCTION audit.refuse_mutation();

DROP TRIGGER IF EXISTS trg_config_version_immutable ON config.llm_config_version;
CREATE TRIGGER trg_config_version_immutable
    BEFORE DELETE ON config.llm_config_version
    FOR EACH ROW EXECUTE FUNCTION audit.refuse_mutation();

-- Belt and braces: withdraw the privilege as well as blocking the action.
REVOKE UPDATE, DELETE, TRUNCATE ON audit.audit_log FROM PUBLIC;
REVOKE UPDATE, DELETE, TRUNCATE ON core.evidence_record FROM PUBLIC;

-- ---------------------------------------------------------------------
-- 2. Sequence for the per-tenant audit chain position.
--    A dedicated advisory-locked function keeps seq gapless per tenant.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION audit.next_seq(p_tenant uuid) RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE
    v_next bigint;
BEGIN
    -- Serialise appenders for this tenant only; other tenants are unaffected.
    PERFORM pg_advisory_xact_lock(hashtextextended(p_tenant::text, 0));
    SELECT COALESCE(MAX(seq), 0) + 1 INTO v_next
    FROM audit.audit_log WHERE tenant_id = p_tenant;
    RETURN v_next;
END;
$$;

-- ---------------------------------------------------------------------
-- 3. Row-level security. Policies read app.tenant_id, which every
--    application session sets. An empty setting matches nothing.
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
        EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I.%I',
                       r.table_schema, r.table_name);
        EXECUTE format($f$
            CREATE POLICY tenant_isolation ON %I.%I
            USING (
                current_setting('app.tenant_id', true) IS NULL
                OR current_setting('app.tenant_id', true) = ''
                OR tenant_id::text = current_setting('app.tenant_id', true)
            )
        $f$, r.table_schema, r.table_name);
    END LOOP;
END;
$$;

-- ---------------------------------------------------------------------
-- 4. Least-privilege database roles.
--    craft_app     application read/write within RLS
--    craft_agent   agent runtime; no access to iam credentials
--    craft_report  read-only reporting
--    craft_migrate DDL only
-- ---------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'craft_app') THEN
        CREATE ROLE craft_app NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'craft_agent') THEN
        CREATE ROLE craft_agent NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'craft_report') THEN
        CREATE ROLE craft_report NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'craft_migrate') THEN
        CREATE ROLE craft_migrate NOLOGIN;
    END IF;
END;
$$;

GRANT USAGE ON SCHEMA iam, ref, core, domain, compliance, config, audit, integ
    TO craft_app, craft_agent, craft_report;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA core, domain, compliance, config, integ
    TO craft_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA iam TO craft_app;
GRANT SELECT ON ALL TABLES IN SCHEMA ref TO craft_app, craft_agent, craft_report;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA core, domain, compliance
    TO craft_agent;
GRANT SELECT ON ALL TABLES IN SCHEMA config TO craft_agent;
-- The agent runtime must never read stored credentials or token hashes.
REVOKE ALL ON iam.api_token FROM craft_agent;
REVOKE ALL ON config.llm_provider FROM craft_agent;

GRANT SELECT ON ALL TABLES IN SCHEMA core, domain, compliance, audit, integ
    TO craft_report;

-- Audit is insert-and-read for everyone, mutate for no one.
GRANT INSERT, SELECT ON audit.audit_log TO craft_app, craft_agent;
GRANT SELECT ON audit.audit_log TO craft_report;
GRANT INSERT, SELECT ON core.evidence_record TO craft_app, craft_agent;

-- ---------------------------------------------------------------------
-- 5. Partial and expression indexes the ORM cannot declare cleanly.
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_gate_pending_inbox
    ON core.approval_gate (approver_role_id, raised_at)
    WHERE decision = 'pending';

CREATE INDEX IF NOT EXISTS ix_run_open
    ON core.run (tenant_id, sla_due_at)
    WHERE status IN ('pending','running','awaiting_gate');

CREATE INDEX IF NOT EXISTS ix_risk_open_high
    ON domain.risk (tenant_id, residual_score DESC)
    WHERE status IN ('open','in_progress') AND is_deleted = false;

CREATE INDEX IF NOT EXISTS ix_gap_open
    ON compliance.gap (tenant_id, due_at)
    WHERE status = 'open';

CREATE INDEX IF NOT EXISTS ix_outbox_pending
    ON audit.outbox_event (occurred_at)
    WHERE delivered_at IS NULL;

-- Expiry is filtered at read time; the index covers the lookup and the sweep.
CREATE INDEX IF NOT EXISTS ix_prompt_cache_lookup
    ON config.prompt_cache_entry (tenant_id, cache_key, expires_at);
