-- 0004_outbox_concurrency.sql
--
-- The relay had two defects that only appear under the configuration this
-- repository actually ships.
--
-- 1. render.yaml starts uvicorn with --workers 2, and every worker starts its
--    own relay. Both selected the same pending rows and both delivered them,
--    so every webhook subscriber received each event twice. A receiver that
--    creates a ticket per event would have created two.
--
-- 2. The whole batch — including the outbound HTTP calls — ran inside a single
--    database transaction. One slow endpoint held that transaction open for
--    the duration, blocking vacuum and holding row locks for as long as the
--    remote server cared to take.
--
-- The fix needs somewhere to record a claim and a per-event retry time, which
-- is what these columns are. Delivery now happens between two short
-- transactions rather than inside one long one.

ALTER TABLE audit.outbox_event
    ADD COLUMN IF NOT EXISTS next_attempt_at timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS claimed_at      timestamptz,
    ADD COLUMN IF NOT EXISTS claimed_by      text;

-- The relay's only hot query: undelivered, due, not exhausted, oldest first.
-- Partial, because delivered events are the overwhelming majority over time
-- and there is no reason to carry them in the index.
CREATE INDEX IF NOT EXISTS ix_outbox_claimable
    ON audit.outbox_event (next_attempt_at, occurred_at)
    WHERE delivered_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_outbox_claimed
    ON audit.outbox_event (claimed_at)
    WHERE delivered_at IS NULL AND claimed_at IS NOT NULL;

COMMENT ON COLUMN audit.outbox_event.claimed_at IS
    'Set when a relay takes the event. A claim older than the reclaim window is '
    'treated as abandoned, so a worker that dies mid-delivery does not strand '
    'its events.';
COMMENT ON COLUMN audit.outbox_event.next_attempt_at IS
    'Earliest time this event may be retried. Backoff is per event, so one '
    'failing subscriber cannot starve everything queued behind it.';

-- The platform API already reported "last succeeded at" for a subscription;
-- the column it read did not exist, so that endpoint raised. Last attempt and
-- last success are different questions and an operator needs both.
ALTER TABLE integ.webhook_subscription
    ADD COLUMN IF NOT EXISTS last_success_at timestamptz;

-- The relay updates these columns, so the application role needs the right.
GRANT SELECT, INSERT, UPDATE ON audit.outbox_event TO craft_app;
