-- 0005_invocation_confidence.sql
--
-- The AI oversight endpoint averaged a confidence column that did not exist,
-- so the endpoint raised on every call. It was written against the design in
-- app/processes rather than against the schema.
--
-- The column is the right fix rather than reading confidence back out of the
-- audit log's JSON detail. Two controls depend on it as a first-class
-- measurement: PR-AIG-02 (human oversight) escalates work below an agent's
-- confidence floor, and PR-AIG-03 (drift) baselines confidence per task class
-- so that a provider changing a model underneath the platform is detectable.
-- A metric that governs a control should be a column, not a JSON field that
-- happens to usually be populated.

ALTER TABLE config.model_invocation
    ADD COLUMN IF NOT EXISTS confidence numeric(4,3);

COMMENT ON COLUMN config.model_invocation.confidence IS
    'The model''s stated confidence in its output, 0-1, where the task asked '
    'for one. Null for deterministic calls. Baselined per task class to detect '
    'drift after a provider-side model change.';

-- The oversight and drift queries both aggregate by task class over a window.
CREATE INDEX IF NOT EXISTS ix_model_invocation_confidence
    ON config.model_invocation (tenant_id, task_class, created_at)
    WHERE confidence IS NOT NULL;
