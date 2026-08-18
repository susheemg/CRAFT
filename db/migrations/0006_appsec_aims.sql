-- 0006_appsec_aims.sql
--
-- Everything the ORM cannot express for the ISO/IEC 27034 application security
-- and ISO/IEC 42001 AI management tables added in app/models/appsec.py and
-- app/models/aims.py.
--
-- The tables themselves come from the metadata. What lives here is the part
-- that has to be true regardless of which code path writes the row:
--
--   1. Row-level security on the new tenant tables, with FORCE, matching 0002.
--   2. Separation of duties on ASC evidence, as a trigger. ISO/IEC 27034-1 8.4
--      separates the project team that performs a security activity from the
--      verification team that measures it. Enforced in the database because a
--      control that lives only in a service method is one refactor from gone.
--   3. Exactly one level zero per ONF iteration — a partial unique index, which
--      a table constraint cannot express.
--   4. An approved AI system impact assessment must name a human approver.
--      ISO/IEC 42001 A.5 assigns that judgement to the organisation, and a
--      fluent draft is not an organisational judgement.
--   5. Grants for the serving credential, which owns nothing and never will.

-- ---------------------------------------------------------------------
-- 1. Row-level security on the new tenant tables
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
          AND (c.table_schema, c.table_name) IN (
              ('compliance','onf'), ('compliance','onf_committee_member'),
              ('compliance','onf_context'), ('compliance','trust_level'),
              ('compliance','asc'), ('compliance','asc_edge'),
              ('compliance','asc_trust_level'), ('compliance','lifecycle_stage_map'),
              ('compliance','anf'), ('compliance','anf_asc'),
              ('compliance','asc_evidence'), ('compliance','soa_entry'),
              ('domain','application'), ('domain','ai_system'),
              ('domain','ai_system_resource'), ('domain','ai_impact_assessment'),
              ('domain','ai_data_provenance'), ('domain','ai_third_party'),
              ('domain','ai_incident_link'),
              ('config','agent_charter'), ('config','agent_tool_grant'),
              ('config','agent_budget_ledger')
          )
    LOOP
        EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',
                       r.table_schema, r.table_name);
        EXECUTE format('ALTER TABLE %I.%I FORCE ROW LEVEL SECURITY',
                       r.table_schema, r.table_name);
        EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I.%I',
                       r.table_schema, r.table_name);
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

-- ---------------------------------------------------------------------
-- 2. Separation of duties on ASC evidence
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION compliance.enforce_asc_sod()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_requires_human boolean;
    v_clash          int;
BEGIN
    IF NEW.kind <> 'measurement' THEN
        RETURN NEW;
    END IF;

    -- Whoever performed the security activity cannot record its verification.
    -- Matched on actor identity rather than on principal type, which is why the
    -- executing agent and the verifying agent are separate identities in the
    -- registry rather than two modes of one agent.
    SELECT count(*) INTO v_clash
    FROM compliance.asc_evidence e
    WHERE e.anf_asc_id = NEW.anf_asc_id
      AND e.kind = 'activity'
      AND (
            (NEW.actor_user_id  IS NOT NULL AND e.actor_user_id  = NEW.actor_user_id)
         OR (NEW.actor_agent_id IS NOT NULL AND e.actor_agent_id = NEW.actor_agent_id)
      );

    IF v_clash > 0 THEN
        RAISE EXCEPTION
            'Separation of duties: this actor performed the security activity for the '
            'ASC and cannot record its verification measurement'
            USING ERRCODE = 'raise_exception';
    END IF;

    -- Some ASCs are not safely verifiable by an agent at all: independent
    -- review, and every control that governs the agent estate itself. An agent
    -- assessing the controls that bound agents is the clearest case where
    -- fluency would be mistaken for assurance.
    SELECT a.measurement_requires_human INTO v_requires_human
    FROM compliance.anf_asc na
    JOIN compliance.asc a ON a.id = na.asc_id
    WHERE na.id = NEW.anf_asc_id;

    IF coalesce(v_requires_human, false) AND NEW.actor_type = 'agent' THEN
        RAISE EXCEPTION
            'This ASC requires a human verifier; an agent-recorded measurement is refused'
            USING ERRCODE = 'raise_exception';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS asc_evidence_sod ON compliance.asc_evidence;
CREATE TRIGGER asc_evidence_sod
    BEFORE INSERT OR UPDATE ON compliance.asc_evidence
    FOR EACH ROW EXECUTE FUNCTION compliance.enforce_asc_sod();

-- ---------------------------------------------------------------------
-- 3. Exactly one level zero per ONF iteration
-- ---------------------------------------------------------------------
-- Level zero is the floor the ONF committee will not let a project go below.
-- Two of them means there is no floor.
CREATE UNIQUE INDEX IF NOT EXISTS uq_trust_level_one_zero
    ON compliance.trust_level (onf_id) WHERE is_level_zero;

-- ---------------------------------------------------------------------
-- 4. An approved impact assessment names a human approver
-- ---------------------------------------------------------------------
ALTER TABLE domain.ai_impact_assessment
    DROP CONSTRAINT IF EXISTS ck_ai_impact_human_approval;
ALTER TABLE domain.ai_impact_assessment
    ADD CONSTRAINT ck_ai_impact_human_approval
    CHECK (
        status <> 'approved'
        OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)
    );

-- An agent may draft. A draft that claims to be human-attested is a lie the
-- evidence base cannot detect later, so the combination is refused outright.
ALTER TABLE domain.ai_impact_assessment
    DROP CONSTRAINT IF EXISTS ck_ai_impact_agent_draft_labelled;
ALTER TABLE domain.ai_impact_assessment
    ADD CONSTRAINT ck_ai_impact_agent_draft_labelled
    CHECK (
        drafted_by_agent_id IS NULL
        OR draft_provenance IN ('ai_generated', 'ai_assisted')
    );

-- The same rule for ASC evidence: an agent-recorded row cannot be labelled as
-- human attestation.
ALTER TABLE compliance.asc_evidence
    DROP CONSTRAINT IF EXISTS ck_asc_evidence_agent_not_attested;
ALTER TABLE compliance.asc_evidence
    ADD CONSTRAINT ck_asc_evidence_agent_not_attested
    CHECK (
        actor_type <> 'agent'
        OR provenance IN ('ai_generated', 'ai_assisted', 'tool_output')
    );

-- ---------------------------------------------------------------------
-- 5. Grants
-- ---------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'craft_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE
            ON ALL TABLES IN SCHEMA compliance, domain, config TO craft_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA compliance, domain, config TO craft_app;
        -- ``ref`` stays read-only. The reference model ships with the code.
        GRANT SELECT ON ALL TABLES IN SCHEMA ref TO craft_app;
    END IF;
END;
$$;
