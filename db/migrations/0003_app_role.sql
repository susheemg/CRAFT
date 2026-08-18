-- 0003_app_role.sql
--
-- The reason the tenant-isolation test kept failing.
--
-- FORCE ROW LEVEL SECURITY in 0002 closed the table-owner exemption, but a
-- PostgreSQL superuser holds BYPASSRLS and is exempt from policies no matter
-- what the table says. As long as the application connects as `postgres`, the
-- tenant policies are decoration.
--
-- So the application gets its own login role that is emphatically not a
-- superuser and does not own the tables. Schema changes run separately, under
-- the owning role, through CRAFT_MIGRATION_DATABASE_URL.
--
-- The practical rule this encodes: the credential that serves requests must
-- not be able to alter the schema, disable a trigger, or read across tenants.

DO $$
DECLARE
    app_password text := coalesce(
        current_setting('craft.app_password', true), 'craft_app_local_dev'
    );
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'craft_app') THEN
        EXECUTE format('ALTER ROLE craft_app LOGIN PASSWORD %L NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE', app_password);
    ELSE
        EXECUTE format('CREATE ROLE craft_app LOGIN PASSWORD %L NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE', app_password);
    END IF;
END;
$$;

-- Usage on the schemas, but no ownership: craft_app cannot DROP or ALTER.
GRANT USAGE ON SCHEMA iam, ref, core, domain, compliance, config, audit, integ
    TO craft_app;

-- Ordinary read/write on the mutable tables.
DO $$
DECLARE
    s text;
BEGIN
    FOREACH s IN ARRAY ARRAY['iam','core','domain','compliance','config','integ'] LOOP
        EXECUTE format(
            'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA %I TO craft_app', s
        );
        EXECUTE format(
            'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO craft_app', s
        );
        -- Tables added by a later migration inherit the same grants.
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I '
            'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO craft_app', s
        );
        EXECUTE format(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA %I '
            'GRANT USAGE, SELECT ON SEQUENCES TO craft_app', s
        );
    END LOOP;
END;
$$;

-- Reference data is read-only to the application; it changes through seeding.
GRANT SELECT ON ALL TABLES IN SCHEMA ref TO craft_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA ref GRANT SELECT ON TABLES TO craft_app;

-- The audit schema is deliberately narrower. Even if the triggers were removed,
-- the application's credential could not update or delete a log entry.
GRANT SELECT, INSERT ON audit.audit_log TO craft_app;
GRANT SELECT, INSERT ON audit.chain_check TO craft_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON audit.outbox_event TO craft_app;
GRANT SELECT ON audit.schema_migration TO craft_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA audit TO craft_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT USAGE, SELECT ON SEQUENCES TO craft_app;

-- Evidence is append-only for the same reason as the log.
REVOKE UPDATE, DELETE ON core.evidence_record FROM craft_app;

COMMENT ON ROLE craft_app IS
    'Application login role. Not a superuser and not a table owner, so row-level '
    'security applies to it. Cannot alter schema, disable triggers, or modify the '
    'audit log.';
