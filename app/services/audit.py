"""The immutable audit log.

Every consequential action appends one row. Rows are chained per tenant:

    row_hash = SHA-256( prev_hash || canonical_json(chained_fields) )

``chained_fields`` deliberately excludes the hashes themselves and includes
everything else that matters — actor, action, entity, before/after state, AI
lineage and the timestamp. Change any of those after the fact and the chain
breaks at that row and at every row after it, which is exactly what
:func:`verify_chain` reports.

Two independent guarantees back this up:

  * the database refuses UPDATE and DELETE on the table (migration 0001)
  * the chain makes any successful tampering detectable and locatable

The append is deliberately synchronous and in the caller's transaction. If the
business change commits, its audit row commits with it; if the audit append
fails, the business change rolls back. An action that cannot be recorded does
not happen.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.audit import AuditChainCheck, AuditLog
from app.models.base import ActorType, utcnow
from app.security.crypto import canonical_json, sha256_hex

log = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64


def _chained_payload(
    *,
    tenant_id: uuid.UUID,
    seq: int,
    actor_type: str,
    actor_ref: str,
    actor_id: Optional[uuid.UUID],
    action: str,
    outcome: str,
    entity: Optional[str],
    entity_id: Optional[uuid.UUID],
    before_state: Any,
    after_state: Any,
    detail: Any,
    model: Optional[str],
    prompt_version: Optional[str],
    sources: Any,
    request_id: Optional[str],
    created_at: datetime,
) -> dict:
    """The exact field set the hash covers. Order-independent: keys are sorted."""
    return {
        "tenant_id": str(tenant_id),
        "seq": seq,
        "actor_type": actor_type,
        "actor_ref": actor_ref,
        "actor_id": str(actor_id) if actor_id else None,
        "action": action,
        "outcome": outcome,
        "entity": entity,
        "entity_id": str(entity_id) if entity_id else None,
        "before_state": before_state,
        "after_state": after_state,
        "detail": detail,
        "model": model,
        "prompt_version": prompt_version,
        "sources": sources,
        "request_id": request_id,
        "created_at": created_at.isoformat(),
    }


def _coerce_ip(value: str | None) -> str | None:
    """Return the value only if it is genuinely an IP address.

    The column is INET, and a proxy or test client can present something that
    is not an address at all. An unparseable client address is not a reason to
    fail an audit write — losing the entry would be far worse than losing the
    address — so it is dropped and the rest of the entry is recorded.
    """
    if not value:
        return None
    import ipaddress

    candidate = value.split(",")[0].strip()
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return None
    return candidate


def record(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    action: str,
    actor_type: ActorType = ActorType.SYSTEM,
    actor_ref: str = "system",
    actor_id: uuid.UUID | None = None,
    outcome: str = "success",
    entity: str | None = None,
    entity_id: uuid.UUID | None = None,
    before_state: Any = None,
    after_state: Any = None,
    detail: Any = None,
    model: str | None = None,
    prompt_version: str | None = None,
    sources: Any = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    on_behalf_of: str | None = None,
) -> AuditLog:
    """Append one audit row inside the caller's transaction."""
    seq = db.execute(
        text("SELECT audit.next_seq(:t)"), {"t": str(tenant_id)}
    ).scalar_one()

    prev_hash = db.execute(
        select(AuditLog.row_hash)
        .where(AuditLog.tenant_id == tenant_id, AuditLog.seq == seq - 1)
    ).scalar_one_or_none() or GENESIS_HASH

    created_at = utcnow()
    payload = _chained_payload(
        tenant_id=tenant_id,
        seq=seq,
        actor_type=actor_type.value,
        actor_ref=actor_ref,
        actor_id=actor_id,
        action=action,
        outcome=outcome,
        entity=entity,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        detail=detail,
        model=model,
        prompt_version=prompt_version,
        sources=sources,
        request_id=request_id,
        created_at=created_at,
    )
    row_hash = sha256_hex(prev_hash + canonical_json(payload))

    entry = AuditLog(
        tenant_id=tenant_id,
        seq=seq,
        actor_type=actor_type,
        actor_ref=actor_ref,
        actor_id=actor_id,
        on_behalf_of=on_behalf_of,
        action=action,
        outcome=outcome,
        entity=entity,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        detail=detail,
        model=model,
        prompt_version=prompt_version,
        sources=sources,
        request_id=request_id,
        ip_address=_coerce_ip(ip_address),
        user_agent=user_agent,
        prev_hash=prev_hash,
        row_hash=row_hash,
        created_at=created_at,
    )
    db.add(entry)
    db.flush()
    return entry


def recompute_hash(row: AuditLog) -> str:
    payload = _chained_payload(
        tenant_id=row.tenant_id,
        seq=row.seq,
        actor_type=row.actor_type.value if hasattr(row.actor_type, "value") else str(row.actor_type),
        actor_ref=row.actor_ref,
        actor_id=row.actor_id,
        action=row.action,
        outcome=row.outcome,
        entity=row.entity,
        entity_id=row.entity_id,
        before_state=row.before_state,
        after_state=row.after_state,
        detail=row.detail,
        model=row.model,
        prompt_version=row.prompt_version,
        sources=row.sources,
        request_id=row.request_id,
        created_at=row.created_at,
    )
    return sha256_hex((row.prev_hash or GENESIS_HASH) + canonical_json(payload))


@dataclass
class ChainReport:
    tenant_id: uuid.UUID
    rows_checked: int
    from_seq: int
    to_seq: int
    is_intact: bool
    first_broken_seq: int | None
    head_hash: str | None
    reason: str | None = None

    def as_dict(self) -> dict:
        return {
            "tenant_id": str(self.tenant_id),
            "rows_checked": self.rows_checked,
            "from_seq": self.from_seq,
            "to_seq": self.to_seq,
            "is_intact": self.is_intact,
            "first_broken_seq": self.first_broken_seq,
            "head_hash": self.head_hash,
            "reason": self.reason,
        }


def verify_chain(
    db: Session,
    tenant_id: uuid.UUID,
    from_seq: int = 1,
    to_seq: int | None = None,
    persist: bool = False,
) -> ChainReport:
    """Recompute the chain and report the first sequence at which it breaks.

    Three failure modes are detected and distinguished:
      * a row whose content no longer matches its stored hash (tampering)
      * a row whose prev_hash does not match the previous row (splice)
      * a missing sequence number (deletion)
    """
    stmt = select(AuditLog).where(
        AuditLog.tenant_id == tenant_id, AuditLog.seq >= from_seq
    )
    if to_seq is not None:
        stmt = stmt.where(AuditLog.seq <= to_seq)
    rows = db.execute(stmt.order_by(AuditLog.seq)).scalars().all()

    if not rows:
        return ChainReport(tenant_id, 0, from_seq, to_seq or from_seq, True, None, None,
                           "No audit rows in range")

    expected_prev = (
        db.execute(
            select(AuditLog.row_hash).where(
                AuditLog.tenant_id == tenant_id, AuditLog.seq == rows[0].seq - 1
            )
        ).scalar_one_or_none()
        or GENESIS_HASH
    )
    expected_seq = rows[0].seq
    broken_at: int | None = None
    reason: str | None = None

    for row in rows:
        if row.seq != expected_seq:
            broken_at, reason = expected_seq, f"Sequence {expected_seq} is missing"
            break
        if (row.prev_hash or GENESIS_HASH) != expected_prev:
            broken_at, reason = row.seq, "Previous-hash link does not match"
            break
        if recompute_hash(row) != row.row_hash:
            broken_at, reason = row.seq, "Row content does not match its recorded hash"
            break
        expected_prev = row.row_hash
        expected_seq += 1

    report = ChainReport(
        tenant_id=tenant_id,
        rows_checked=len(rows),
        from_seq=rows[0].seq,
        to_seq=rows[-1].seq,
        is_intact=broken_at is None,
        first_broken_seq=broken_at,
        head_hash=rows[-1].row_hash if broken_at is None else None,
        reason=reason,
    )

    if persist:
        db.add(
            AuditChainCheck(
                tenant_id=tenant_id,
                checked_at=utcnow(),
                from_seq=report.from_seq,
                to_seq=report.to_seq,
                rows_checked=report.rows_checked,
                is_intact=report.is_intact,
                first_broken_seq=report.first_broken_seq,
                head_hash=report.head_hash,
                detail={"reason": reason} if reason else None,
            )
        )
        db.flush()
    if not report.is_intact:
        log.error(
            "Audit chain integrity failure for tenant %s at seq %s: %s",
            tenant_id, broken_at, reason,
        )
    return report


def head(db: Session, tenant_id: uuid.UUID) -> tuple[int, str | None]:
    """Current chain length and head hash — cheap enough to expose on a dashboard."""
    row = db.execute(
        select(func.max(AuditLog.seq)).where(AuditLog.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if not row:
        return 0, None
    h = db.execute(
        select(AuditLog.row_hash).where(
            AuditLog.tenant_id == tenant_id, AuditLog.seq == row
        )
    ).scalar_one()
    return row, h
