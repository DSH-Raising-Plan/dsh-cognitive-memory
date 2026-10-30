# -*- coding: utf-8 -*-
"""MemoryService — 唯一业务核心（MCP / REST 共用）。"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from mnemosyne.domain.models import (
    ContextBuildIn,
    ContextBuildOut,
    Evidence,
    EvidenceIn,
    FeedbackIn,
    Memory,
    MemoryProposeIn,
    MemoryStatus,
    MemoryType,
    MemoryUpdateIn,
    Observation,
    ObservationIn,
    ObservationStatus,
    RelationKind,
    SearchQuery,
    Task,
    TaskCreateIn,
)
from mnemosyne.events.bus import EventBus
from mnemosyne.storage.db import Database
from mnemosyne.storage.ids import new_id


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _loads(s: str | None, default: Any) -> Any:
    if not s:
        return default
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return default


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_QUERY_SPLIT_RE = re.compile(r"[\s,，。.!！?？;；:：/\\|]+")


def _query_terms(query: str, *, max_terms: int = 12) -> list[str]:
    """Chinese has no spaces; derive 2-char shingles for LIKE fallback."""
    terms: list[str] = []
    for token in _QUERY_SPLIT_RE.split(query or ""):
        token = token.strip()
        if not token:
            continue
        if _CJK_RE.search(token):
            if len(token) <= 2:
                terms.append(token)
            else:
                terms.extend(token[i:i + 2] for i in range(len(token) - 1))
        else:
            terms.append(token)
    seen: set[str] = set()
    out: list[str] = []
    for term in terms:
        if term not in seen:
            seen.add(term)
            out.append(term)
        if len(out) >= max_terms:
            break
    return out


class ConflictError(Exception):
    def __init__(self, message: str, *, code: str = "conflict"):
        super().__init__(message)
        self.code = code


class NotFoundError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.code = "not_found"


class MemoryService:
    def __init__(
        self,
        db: Database,
        bus: EventBus | None = None,
        *,
        context_token_budget: int = 1200,
    ):
        self.db = db
        self.bus = bus or EventBus()
        self.context_token_budget = context_token_budget
        self.db.ensure_schema()

    # ---------- helpers ----------

    def _row_memory(self, row: sqlite3.Row) -> Memory:
        keys = set(row.keys())
        return Memory(
            id=row["id"],
            type=MemoryType(row["type"]),
            status=MemoryStatus(row["status"]),
            content=row["content"],
            source_ids=_loads(row["source_ids_json"], []),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_confirmed_at=row["last_confirmed_at"],
            version=int(row["version"]),
            confidence=row["confidence"],
            expires_at=row["expires_at"],
            event_time=row["event_time"] if "event_time" in keys else None,
            valid_from=row["valid_from"] if "valid_from" in keys else None,
            valid_until=row["valid_until"] if "valid_until" in keys else None,
            metadata=_loads(row["metadata_json"], {}),
        )

    def _idempotent_get(self, conn: sqlite3.Connection, key: str | None, scope: str) -> Any | None:
        if not key:
            return None
        row = conn.execute(
            "SELECT response_json FROM idempotency_keys WHERE key=? AND scope=?",
            (key, scope),
        ).fetchone()
        if not row:
            return None
        return _loads(row["response_json"], None)

    def _idempotent_put(
        self, conn: sqlite3.Connection, key: str | None, scope: str, response: Any
    ) -> None:
        if not key:
            return
        conn.execute(
            """
            INSERT OR REPLACE INTO idempotency_keys(key, scope, response_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (key, scope, json.dumps(response, ensure_ascii=False), _now()),
        )

    def _emit(
        self,
        conn: sqlite3.Connection,
        event_type: str,
        payload: dict[str, Any],
        *,
        producer: str = "mnemosyne",
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> str:
        eid = new_id("evt")
        now = _now()
        envelope = {
            "event_id": eid,
            "event_type": event_type,
            "event_version": 1,
            "occurred_at": now,
            "recorded_at": now,
            "producer": producer,
            "correlation_id": correlation_id,
            "causation_id": causation_id,
            "payload_version": 1,
            "payload": payload,
        }
        conn.execute(
            """
            INSERT INTO events(
              event_id, event_type, event_version, occurred_at, recorded_at,
              producer, correlation_id, causation_id, payload_version, payload_json
            ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                eid,
                event_type,
                now,
                now,
                producer,
                correlation_id,
                causation_id,
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        conn.execute(
            """
            INSERT INTO outbox(event_id, status, attempts, next_attempt_at, created_at, updated_at)
            VALUES (?, 'pending', 0, ?, ?, ?)
            """,
            (eid, now, now, now),
        )
        return eid

    def _snapshot_version(self, conn: sqlite3.Connection, mem: Memory) -> None:
        conn.execute(
            """
            INSERT OR REPLACE INTO memory_versions(memory_id, version, snapshot_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (mem.id, mem.version, mem.model_dump_json(), _now()),
        )

    def _fts_upsert(self, conn: sqlite3.Connection, mem: Memory) -> None:
        conn.execute("DELETE FROM memories_fts WHERE memory_id=?", (mem.id,))
        if mem.status in (MemoryStatus.INVALIDATED, MemoryStatus.ARCHIVED):
            return
        conn.execute(
            "INSERT INTO memories_fts(memory_id, content, type, status) VALUES (?, ?, ?, ?)",
            (mem.id, mem.content, mem.type.value, mem.status.value),
        )

    def _insert_evidence_conn(
        self,
        conn: sqlite3.Connection,
        body: EvidenceIn,
    ) -> Evidence:
        eid = new_id("evd")
        now = _now()
        et = body.evidence_type.value if isinstance(body.evidence_type, RelationKind) else str(body.evidence_type)
        conn.execute(
            """
            INSERT OR IGNORE INTO evidences(
              id, subject_kind, subject_id, source_type, source_id, evidence_type,
              content_ref, confidence, observed_at, recorded_at, provenance_json, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eid,
                body.subject_kind,
                body.subject_id,
                body.source_type,
                body.source_id,
                et,
                body.content_ref,
                body.confidence,
                body.observed_at or now,
                now,
                json.dumps(body.provenance, ensure_ascii=False),
                json.dumps(body.metadata, ensure_ascii=False),
            ),
        )
        # 兼容旧表：memory + observation
        if body.subject_kind == "memory" and body.source_type == "observation":
            conn.execute(
                """
                INSERT OR IGNORE INTO memory_evidence(memory_id, observation_id, relation, note, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (body.subject_id, body.source_id, et, "", now),
            )
        row = conn.execute(
            """
            SELECT id FROM evidences
            WHERE subject_kind=? AND subject_id=? AND source_type=? AND source_id=? AND evidence_type=?
            """,
            (body.subject_kind, body.subject_id, body.source_type, body.source_id, et),
        ).fetchone()
        real_id = row["id"] if row else eid
        return Evidence(
            id=real_id,
            recorded_at=now,
            subject_kind=body.subject_kind,
            subject_id=body.subject_id,
            source_type=body.source_type,
            source_id=body.source_id,
            evidence_type=RelationKind(et) if et in RelationKind._value2member_map_ else RelationKind.SUPPORTS,
            content_ref=body.content_ref,
            confidence=body.confidence,
            observed_at=body.observed_at or now,
            provenance=body.provenance,
            metadata=body.metadata,
        )

    # ---------- observations ----------

    def capture_observation(self, body: ObservationIn) -> Observation:
        with self.db.transaction() as conn:
            cached = self._idempotent_get(conn, body.idempotency_key, "observation")
            if cached:
                return Observation.model_validate(cached)
            oid = new_id("obs")
            now = _now()
            status = ObservationStatus.OBSERVED
            conn.execute(
                """
                INSERT INTO observations(
                  id, source_kind, content, occurred_at, created_at, producer,
                  correlation_id, data_ref, metadata_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    oid,
                    body.source_kind.value,
                    body.content,
                    body.occurred_at or now,
                    now,
                    body.producer,
                    body.correlation_id,
                    body.data_ref,
                    json.dumps(body.metadata, ensure_ascii=False),
                    status.value,
                ),
            )
            obs = Observation(
                id=oid,
                created_at=now,
                status=status,
                **body.model_dump(exclude={"idempotency_key"}),
            )
            self._emit(
                conn,
                "observation.captured",
                {"observation_id": oid, "source_kind": body.source_kind.value},
                producer=body.producer,
                correlation_id=body.correlation_id,
            )
            # 快速通道：对话类观察同步写一条 working 记忆
            if body.source_kind.value in ("dialog", "user_statement"):
                wid = new_id("mem")
                wm = Memory(
                    id=wid,
                    type=MemoryType.WORKING,
                    status=MemoryStatus.ACTIVE,
                    content=body.content[:2000],
                    source_ids=[oid],
                    created_at=now,
                    updated_at=now,
                    last_confirmed_at=now,
                    version=1,
                    metadata={"from_observation": oid},
                )
                self._insert_memory(conn, wm)
                self._emit(
                    conn,
                    "memory.activated",
                    {"memory_id": wid, "type": "working"},
                    producer=body.producer,
                    correlation_id=body.correlation_id,
                )
            # 慢速：请求归纳
            self._create_task_conn(
                conn,
                TaskCreateIn(
                    task_type="memory.consolidation",
                    payload={"observation_id": oid},
                ),
            )
            payload = obs.model_dump()
            self._idempotent_put(conn, body.idempotency_key, "observation", payload)
            return obs

    def get_observation(self, observation_id: str) -> dict[str, Any] | None:
        row = self.db.connect().execute(
            "SELECT * FROM observations WHERE id=?", (observation_id,)
        ).fetchone()
        if not row:
            return None
        keys = set(row.keys())
        return {
            "id": row["id"],
            "source_kind": row["source_kind"],
            "content": row["content"],
            "occurred_at": row["occurred_at"],
            "created_at": row["created_at"],
            "producer": row["producer"],
            "correlation_id": row["correlation_id"],
            "data_ref": row["data_ref"],
            "metadata": _loads(row["metadata_json"], {}),
            "status": row["status"] if "status" in keys else ObservationStatus.OBSERVED.value,
        }

    def set_observation_status(self, observation_id: str, status: ObservationStatus | str) -> dict[str, Any]:
        st = status.value if isinstance(status, ObservationStatus) else str(status)
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT id FROM observations WHERE id=?", (observation_id,)
            ).fetchone()
            if not row:
                raise NotFoundError(f"observation not found: {observation_id}")
            conn.execute(
                "UPDATE observations SET status=? WHERE id=?",
                (st, observation_id),
            )
        out = self.get_observation(observation_id) or {}
        return out

    def add_evidence(self, body: EvidenceIn) -> Evidence:
        with self.db.transaction() as conn:
            ev = self._insert_evidence_conn(conn, body)
            self._emit(
                conn,
                "evidence.added",
                {
                    "evidence_id": ev.id,
                    "subject_id": body.subject_id,
                    "evidence_type": ev.evidence_type.value,
                },
            )
            return ev

    def list_evidence(
        self,
        *,
        subject_kind: str = "memory",
        subject_id: str,
        evidence_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        lim = max(1, min(500, int(limit or 100)))
        conn = self.db.connect()
        sql = "SELECT * FROM evidences WHERE subject_kind=? AND subject_id=?"
        args: list[Any] = [subject_kind, subject_id]
        if evidence_type:
            sql += " AND evidence_type=?"
            args.append(evidence_type)
        sql += " ORDER BY recorded_at DESC LIMIT ?"
        args.append(lim)
        try:
            rows = conn.execute(sql, tuple(args)).fetchall()
        except sqlite3.OperationalError:
            return []
        out: list[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": r["id"],
                    "subject_kind": r["subject_kind"],
                    "subject_id": r["subject_id"],
                    "source_type": r["source_type"],
                    "source_id": r["source_id"],
                    "evidence_type": r["evidence_type"],
                    "content_ref": r["content_ref"],
                    "confidence": r["confidence"],
                    "observed_at": r["observed_at"],
                    "recorded_at": r["recorded_at"],
                    "provenance": _loads(r["provenance_json"], {}),
                    "metadata": _loads(r["metadata_json"], {}),
                }
            )
        return out

    def list_decision_logs(self, *, subject_id: str | None = None, limit: int = 40) -> list[dict[str, Any]]:
        from mnemosyne.cognition.decision_log import list_decisions

        return list_decisions(self.db, subject_id=subject_id, limit=limit)

    # ---------- memories ----------

    def _insert_memory(self, conn: sqlite3.Connection, mem: Memory) -> None:
        conn.execute(
            """
            INSERT INTO memories(
              id, type, status, content, source_ids_json, created_at, updated_at,
              last_confirmed_at, version, confidence, expires_at, metadata_json,
              event_time, valid_from, valid_until
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mem.id,
                mem.type.value,
                mem.status.value,
                mem.content,
                json.dumps(mem.source_ids, ensure_ascii=False),
                mem.created_at,
                mem.updated_at,
                mem.last_confirmed_at,
                mem.version,
                mem.confidence,
                mem.expires_at,
                json.dumps(mem.metadata, ensure_ascii=False),
                mem.event_time,
                mem.valid_from,
                mem.valid_until,
            ),
        )
        self._snapshot_version(conn, mem)
        self._fts_upsert(conn, mem)
        for sid in mem.source_ids:
            self._insert_evidence_conn(
                conn,
                EvidenceIn(
                    subject_kind="memory",
                    subject_id=mem.id,
                    source_type="observation",
                    source_id=sid,
                    evidence_type=RelationKind.SUPPORTS,
                ),
            )

    def propose_memory(self, body: MemoryProposeIn) -> Memory:
        with self.db.transaction() as conn:
            cached = self._idempotent_get(conn, body.idempotency_key, "memory_propose")
            if cached:
                return Memory.model_validate(cached)
            now = _now()
            mid = new_id("mem")
            mem = Memory(
                id=mid,
                type=body.type,
                status=body.status,
                content=body.content,
                source_ids=list(body.source_ids),
                created_at=now,
                updated_at=now,
                last_confirmed_at=now if body.status == MemoryStatus.ACTIVE else None,
                version=1,
                confidence=body.confidence,
                expires_at=body.expires_at,
                event_time=body.event_time,
                valid_from=body.valid_from,
                valid_until=body.valid_until,
                metadata=body.metadata,
            )
            self._insert_memory(conn, mem)
            self._emit(
                conn,
                "memory.candidate_created"
                if body.status == MemoryStatus.CANDIDATE
                else "memory.activated",
                {"memory_id": mid, "type": body.type.value, "status": body.status.value},
            )
            if body.status == MemoryStatus.CANDIDATE:
                self._create_task_conn(
                    conn,
                    TaskCreateIn(
                        task_type="memory.promote_check",
                        payload={"memory_id": mid},
                    ),
                )
            payload = mem.model_dump()
            self._idempotent_put(conn, body.idempotency_key, "memory_propose", payload)
            return mem

    def get_memory(self, memory_id: str, *, include_evidence: bool = False) -> dict[str, Any]:
        conn = self.db.connect()
        row = conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            raise NotFoundError(f"memory not found: {memory_id}")
        mem = self._row_memory(row)
        out = mem.model_dump()
        if include_evidence:
            ev = conn.execute(
                "SELECT observation_id, relation, note, created_at FROM memory_evidence WHERE memory_id=?",
                (memory_id,),
            ).fetchall()
            out["evidence"] = [dict(r) for r in ev]
            vers = conn.execute(
                "SELECT version, created_at FROM memory_versions WHERE memory_id=? ORDER BY version",
                (memory_id,),
            ).fetchall()
            out["versions"] = [dict(r) for r in vers]
        return out

    def update_memory(self, memory_id: str, body: MemoryUpdateIn) -> Memory:
        with self.db.transaction() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
            if not row:
                raise NotFoundError(f"memory not found: {memory_id}")
            mem = self._row_memory(row)
            if body.expected_version is not None and body.expected_version != mem.version:
                raise ConflictError(
                    f"version mismatch: expected {body.expected_version}, got {mem.version}",
                    code="version_conflict",
                )
            if body.content is not None:
                mem.content = body.content
            if body.status is not None:
                mem.status = body.status
            if body.metadata is not None:
                mem.metadata = body.metadata
            if body.confidence is not None:
                mem.confidence = body.confidence
            if body.expires_at is not None:
                mem.expires_at = body.expires_at
            if body.event_time is not None:
                mem.event_time = body.event_time
            if body.valid_from is not None:
                mem.valid_from = body.valid_from
            if body.valid_until is not None:
                mem.valid_until = body.valid_until
            mem.version += 1
            mem.updated_at = _now()
            if mem.status == MemoryStatus.ACTIVE:
                mem.last_confirmed_at = mem.updated_at
            conn.execute(
                """
                UPDATE memories SET
                  content=?, status=?, metadata_json=?, confidence=?, expires_at=?,
                  event_time=?, valid_from=?, valid_until=?,
                  version=?, updated_at=?, last_confirmed_at=?
                WHERE id=?
                """,
                (
                    mem.content,
                    mem.status.value,
                    json.dumps(mem.metadata, ensure_ascii=False),
                    mem.confidence,
                    mem.expires_at,
                    mem.event_time,
                    mem.valid_from,
                    mem.valid_until,
                    mem.version,
                    mem.updated_at,
                    mem.last_confirmed_at,
                    mem.id,
                ),
            )
            self._snapshot_version(conn, mem)
            self._fts_upsert(conn, mem)
            et = (
                "memory.invalidated"
                if mem.status == MemoryStatus.INVALIDATED
                else "memory.updated"
            )
            self._emit(conn, et, {"memory_id": mem.id, "version": mem.version})
            return mem

    def _cancel_tasks_for_resource(
        self,
        conn: sqlite3.Connection,
        *,
        observation_id: str | None = None,
        memory_id: str | None = None,
    ) -> int:
        """取消仍可能重生已删内容的 pending/running 任务。"""
        rows = conn.execute(
            "SELECT id, payload_json FROM tasks WHERE status IN ('pending','running')"
        ).fetchall()
        n = 0
        now = _now()
        for row in rows:
            payload = _loads(row["payload_json"], {})
            hit = False
            if observation_id and payload.get("observation_id") == observation_id:
                hit = True
            if memory_id and payload.get("memory_id") == memory_id:
                hit = True
            if not hit:
                continue
            conn.execute(
                """
                UPDATE tasks SET status='cancelled', last_error=?, updated_at=?
                WHERE id=?
                """,
                ("resource_deleted", now, row["id"]),
            )
            n += 1
        return n

    def _scrub_schema_memory_refs(self, conn: sqlite3.Connection, memory_id: str) -> int:
        """从 cognitive_schemas JSON 中移除 memory_id 引用（无法重建正文）。"""
        try:
            rows = conn.execute("SELECT id, payload_json FROM cognitive_schemas").fetchall()
        except sqlite3.OperationalError:
            return 0
        n = 0
        now = _now()
        for row in rows:
            payload = _loads(row["payload_json"], {})
            changed = False
            evid = dict(payload.get("evidence") or {})
            for key in ("supporting", "counter", "memory_ids", "evidenceRefs"):
                if key in evid and isinstance(evid[key], list):
                    new_list = [x for x in evid[key] if str(x) != memory_id]
                    if len(new_list) != len(evid[key]):
                        evid[key] = new_list
                        changed = True
                if key in payload and isinstance(payload[key], list):
                    new_list = [x for x in payload[key] if str(x) != memory_id]
                    if len(new_list) != len(payload[key]):
                        payload[key] = new_list
                        changed = True
            if evid:
                payload["evidence"] = evid
            if not changed:
                continue
            conn.execute(
                "UPDATE cognitive_schemas SET payload_json=?, updated_at=? WHERE id=?",
                (json.dumps(payload, ensure_ascii=False), now, row["id"]),
            )
            n += 1
        return n

    def _hard_delete_memory_conn(self, conn: sqlite3.Connection, memory_id: str) -> dict[str, Any]:
        row = conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
        if not row:
            return {"id": memory_id, "deleted": False, "detail": "not_found"}
        conn.execute("DELETE FROM memories_fts WHERE memory_id=?", (memory_id,))
        conn.execute("DELETE FROM memory_evidence WHERE memory_id=?", (memory_id,))
        conn.execute("DELETE FROM memory_feedback WHERE memory_id=?", (memory_id,))
        try:
            conn.execute(
                "DELETE FROM evidences WHERE subject_kind='memory' AND subject_id=?",
                (memory_id,),
            )
        except sqlite3.OperationalError:
            pass
        conn.execute(
            "DELETE FROM memory_relations WHERE from_id=? OR to_id=?",
            (memory_id, memory_id),
        )
        # 隐私遗忘：清除可重建正文的版本快照
        conn.execute("DELETE FROM memory_versions WHERE memory_id=?", (memory_id,))
        schema_scrubbed = self._scrub_schema_memory_refs(conn, memory_id)
        cancelled = self._cancel_tasks_for_resource(conn, memory_id=memory_id)
        conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        self._emit(
            conn,
            "memory.forgotten",
            {
                "memory_id": memory_id,
                "hard": True,
                "schema_scrubbed": schema_scrubbed,
                "tasks_cancelled": cancelled,
            },
        )
        return {
            "id": memory_id,
            "deleted": True,
            "hard": True,
            "schema_scrubbed": schema_scrubbed,
            "tasks_cancelled": cancelled,
        }

    def forget_memory(self, memory_id: str, *, hard: bool = False) -> dict[str, Any]:
        """软删除：invalidated；hard：清除主表/FTS/证据/关系/版本/schema 引用。"""
        if not hard:
            return self.update_memory(
                memory_id,
                MemoryUpdateIn(status=MemoryStatus.INVALIDATED),
            ).model_dump()
        with self.db.transaction() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,)).fetchone()
            if not row:
                raise NotFoundError(f"memory not found: {memory_id}")
            return self._hard_delete_memory_conn(conn, memory_id)

    def build_deletion_plan(
        self,
        *,
        observation_id: str | None = None,
        memory_id: str | None = None,
        hard: bool = True,
    ) -> dict[str, Any]:
        """只读：展示删除影响范围（不执行）。"""
        conn = self.db.connect()
        plan: dict[str, Any] = {
            "hard": hard,
            "observation_id": observation_id,
            "memory_id": memory_id,
            "memories": [],
            "evidence_links": 0,
            "relations": 0,
            "pending_tasks": 0,
            "schema_refs": 0,
        }
        mem_ids: set[str] = set()
        if memory_id:
            mem_ids.add(memory_id)
        if observation_id:
            for r in conn.execute(
                "SELECT memory_id FROM memory_evidence WHERE observation_id=?",
                (observation_id,),
            ).fetchall():
                mem_ids.add(r["memory_id"])
            for r in conn.execute("SELECT id, source_ids_json FROM memories").fetchall():
                sids = _loads(r["source_ids_json"], [])
                if observation_id in sids:
                    mem_ids.add(r["id"])
        plan["memories"] = sorted(mem_ids)
        if mem_ids:
            placeholders = ",".join("?" * len(mem_ids))
            plan["evidence_links"] = conn.execute(
                f"SELECT COUNT(*) AS n FROM memory_evidence WHERE memory_id IN ({placeholders})",
                tuple(mem_ids),
            ).fetchone()["n"]
            plan["relations"] = conn.execute(
                f"""
                SELECT COUNT(*) AS n FROM memory_relations
                WHERE from_id IN ({placeholders}) OR to_id IN ({placeholders})
                """,
                tuple(mem_ids) + tuple(mem_ids),
            ).fetchone()["n"]
        # pending tasks
        for r in conn.execute(
            "SELECT payload_json FROM tasks WHERE status IN ('pending','running')"
        ).fetchall():
            p = _loads(r["payload_json"], {})
            if observation_id and p.get("observation_id") == observation_id:
                plan["pending_tasks"] += 1
            elif memory_id and p.get("memory_id") == memory_id:
                plan["pending_tasks"] += 1
            elif p.get("memory_id") in mem_ids or p.get("observation_id") == observation_id:
                plan["pending_tasks"] += 1
        try:
            for r in conn.execute("SELECT payload_json FROM cognitive_schemas").fetchall():
                blob = json.dumps(_loads(r["payload_json"], {}), ensure_ascii=False)
                if any(mid in blob for mid in mem_ids):
                    plan["schema_refs"] += 1
        except sqlite3.OperationalError:
            pass
        return plan

    def delete_observation(
        self,
        observation_id: str,
        *,
        hard: bool = True,
        cascade_memories: bool = True,
    ) -> dict[str, Any]:
        """删除观察；默认级联 hard-forget 仅以该观察为唯一来源的派生记忆。"""
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM observations WHERE id=?", (observation_id,)
            ).fetchone()
            if not row:
                raise NotFoundError(f"observation not found: {observation_id}")

            linked = [
                r["memory_id"]
                for r in conn.execute(
                    "SELECT DISTINCT memory_id FROM memory_evidence WHERE observation_id=?",
                    (observation_id,),
                ).fetchall()
            ]
            # 也扫 source_ids
            for r in conn.execute("SELECT id, source_ids_json FROM memories").fetchall():
                sids = _loads(r["source_ids_json"], [])
                if observation_id in sids and r["id"] not in linked:
                    linked.append(r["id"])

            forgotten: list[dict[str, Any]] = []
            invalidated: list[str] = []
            if cascade_memories:
                for mid in linked:
                    ev_rows = conn.execute(
                        "SELECT observation_id FROM memory_evidence WHERE memory_id=?",
                        (mid,),
                    ).fetchall()
                    other_sources = [
                        e["observation_id"] for e in ev_rows if e["observation_id"] != observation_id
                    ]
                    if hard and not other_sources:
                        forgotten.append(self._hard_delete_memory_conn(conn, mid))
                    else:
                        # 去掉该观察证据；若仍有其他来源则仅剥离链接
                        conn.execute(
                            "DELETE FROM memory_evidence WHERE memory_id=? AND observation_id=?",
                            (mid, observation_id),
                        )
                        mem = conn.execute(
                            "SELECT source_ids_json, version FROM memories WHERE id=?",
                            (mid,),
                        ).fetchone()
                        if mem:
                            sids = [s for s in _loads(mem["source_ids_json"], []) if s != observation_id]
                            conn.execute(
                                "UPDATE memories SET source_ids_json=?, updated_at=? WHERE id=?",
                                (json.dumps(sids, ensure_ascii=False), _now(), mid),
                            )
                        if hard and not other_sources:
                            pass
                        elif not other_sources:
                            conn.execute(
                                "UPDATE memories SET status=?, updated_at=? WHERE id=?",
                                (MemoryStatus.INVALIDATED.value, _now(), mid),
                            )
                            invalidated.append(mid)

            cancelled = self._cancel_tasks_for_resource(conn, observation_id=observation_id)
            conn.execute("DELETE FROM memory_evidence WHERE observation_id=?", (observation_id,))
            conn.execute("DELETE FROM observations WHERE id=?", (observation_id,))
            self._emit(
                conn,
                "observation.deleted",
                {
                    "observation_id": observation_id,
                    "hard": hard,
                    "forgotten": [f.get("id") for f in forgotten],
                    "invalidated": invalidated,
                    "tasks_cancelled": cancelled,
                },
            )
            return {
                "observation_id": observation_id,
                "deleted": True,
                "hard": hard,
                "forgotten_memories": forgotten,
                "invalidated_memories": invalidated,
                "tasks_cancelled": cancelled,
            }

    def search(self, q: SearchQuery) -> list[Memory]:
        conn = self.db.connect()
        limit = max(1, min(50, int(q.limit or 10)))
        statuses = [s.value for s in (q.status or [MemoryStatus.ACTIVE, MemoryStatus.CANDIDATE])]
        types = [t.value for t in (q.types or list(MemoryType))]
        query = (q.query or "").strip()
        rows: list[sqlite3.Row]
        if query:
            # FTS5：简单转义双引号
            safe = query.replace('"', '""')
            # FTS5：多词用 AND；失败则降级 LIKE
            fts_q = " AND ".join(
                f'"{t.replace(chr(34), "")}"' for t in safe.split() if t.strip()
            ) or f'"{safe}"'
            sql = """
              SELECT m.* FROM memories_fts f
              JOIN memories m ON m.id = f.memory_id
              WHERE f MATCH ?
                AND m.status IN ({sts})
                AND m.type IN ({tys})
              LIMIT ?
            """.format(
                sts=",".join("?" * len(statuses)),
                tys=",".join("?" * len(types)),
            )
            try:
                rows = conn.execute(
                    sql, (fts_q, *statuses, *types, limit)
                ).fetchall()
            except (sqlite3.OperationalError, SystemError):
                # Some Python/SQLite builds raise SystemError for a NULL FTS
                # result instead of an sqlite3 error; degrade to LIKE either way.
                rows = []
            if not rows:
                # 降级：LIKE
                like = f"%{query}%"
                rows = conn.execute(
                    f"""
                    SELECT * FROM memories
                    WHERE content LIKE ?
                      AND status IN ({",".join("?" * len(statuses))})
                      AND type IN ({",".join("?" * len(types))})
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (like, *statuses, *types, limit),
                ).fetchall()
                if not rows:
                    # 中文没有空格：整句 FTS/LIKE 都命中不了时，用 2 字滑窗再试一次
                    terms = _query_terms(query)
                    if terms:
                        likes = " OR ".join(["content LIKE ?"] * len(terms))
                        rows = conn.execute(
                            f"""
                            SELECT * FROM memories
                            WHERE ({likes})
                              AND status IN ({",".join("?" * len(statuses))})
                              AND type IN ({",".join("?" * len(types))})
                            ORDER BY updated_at DESC
                            LIMIT ?
                            """,
                            (*[f"%{t}%" for t in terms], *statuses, *types, limit),
                        ).fetchall()
        else:
            rows = conn.execute(
                f"""
                SELECT * FROM memories
                WHERE status IN ({",".join("?" * len(statuses))})
                  AND type IN ({",".join("?" * len(types))})
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (*statuses, *types, limit),
            ).fetchall()
        return [self._row_memory(r) for r in rows]

    def build_context(self, body: ContextBuildIn) -> ContextBuildOut:
        budget = body.token_budget or self.context_token_budget
        hits = self.search(
            SearchQuery(
                query=body.query,
                types=body.types,
                limit=body.limit,
            )
        )
        fragments: list[dict[str, Any]] = []
        used = 0
        lines: list[str] = ["【演化记忆·仅供参考】"]
        for m in hits:
            est = max(1, len(m.content) // 2)
            if used + est > budget and fragments:
                break
            frag = {
                "id": m.id,
                "type": m.type.value,
                "status": m.status.value,
                "content": m.content,
                "version": m.version,
                "source_ids": m.source_ids,
                "token_estimate": est,
            }
            fragments.append(frag)
            used += est
            lines.append(f"- [{m.type.value}] {m.content}")
        return ContextBuildOut(
            fragments=fragments,
            token_estimate=used,
            brief="\n".join(lines) if fragments else "【演化记忆】暂无相关条目",
        )

    def feedback(self, body: FeedbackIn) -> dict[str, Any]:
        with self.db.transaction() as conn:
            row = conn.execute("SELECT id FROM memories WHERE id=?", (body.memory_id,)).fetchone()
            if not row:
                raise NotFoundError(f"memory not found: {body.memory_id}")
            now = _now()
            conn.execute(
                """
                INSERT INTO memory_feedback(memory_id, useful, incorrect, note, producer, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    body.memory_id,
                    None if body.useful is None else int(bool(body.useful)),
                    None if body.incorrect is None else int(bool(body.incorrect)),
                    body.note,
                    body.producer,
                    now,
                ),
            )
            self._emit(
                conn,
                "memory.feedback_received",
                {
                    "memory_id": body.memory_id,
                    "useful": body.useful,
                    "incorrect": body.incorrect,
                },
                producer=body.producer,
            )
            if body.incorrect:
                self._create_task_conn(
                    conn,
                    TaskCreateIn(
                        task_type="memory.review_feedback",
                        payload={"memory_id": body.memory_id, "note": body.note},
                    ),
                )
            return {"ok": True, "memory_id": body.memory_id}

    # ---------- tasks ----------

    def _create_task_conn(self, conn: sqlite3.Connection, body: TaskCreateIn) -> Task:
        cached = self._idempotent_get(conn, body.idempotency_key, "task")
        if cached:
            return Task.model_validate(cached)
        tid = new_id("task")
        now = _now()
        conn.execute(
            """
            INSERT INTO tasks(id, task_type, status, payload_json, attempts, created_at, updated_at, next_attempt_at)
            VALUES (?, ?, 'pending', ?, 0, ?, ?, ?)
            """,
            (tid, body.task_type, json.dumps(body.payload, ensure_ascii=False), now, now, now),
        )
        task = Task(
            id=tid,
            task_type=body.task_type,
            status="pending",
            payload=body.payload,
            created_at=now,
            updated_at=now,
        )
        self._idempotent_put(conn, body.idempotency_key, "task", task.model_dump())
        return task

    def create_task(self, body: TaskCreateIn) -> Task:
        with self.db.transaction() as conn:
            return self._create_task_conn(conn, body)

    def get_task(self, task_id: str) -> Task:
        row = self.db.connect().execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not row:
            raise NotFoundError(f"task not found: {task_id}")
        return Task(
            id=row["id"],
            task_type=row["task_type"],
            status=row["status"],
            payload=_loads(row["payload_json"], {}),
            attempts=int(row["attempts"]),
            last_error=row["last_error"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def health(self) -> dict[str, Any]:
        conn = self.db.connect()
        mem_n = conn.execute("SELECT COUNT(*) AS n FROM memories").fetchone()["n"]
        obs_n = conn.execute("SELECT COUNT(*) AS n FROM observations").fetchone()["n"]
        pending = conn.execute(
            "SELECT COUNT(*) AS n FROM outbox WHERE status='pending'"
        ).fetchone()["n"]
        return {
            "ok": True,
            "service": "mnemosyne",
            "version": "0.2.0",
            "memories": mem_n,
            "observations": obs_n,
            "outbox_pending": pending,
            "schemas": self.count_cognitive_schemas(),
            "mnemosyne_version": "2.0",
            "time": _now(),
        }

    _RELATION_TYPES = frozenset(
        {"supports", "contradicts", "derives", "supersedes", "before", "after", "continues"}
    )

    def link_memories(
        self,
        *,
        from_id: str,
        to_id: str,
        relation: str,
        note: str = "",
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        rel = (relation or "").strip().lower()
        if rel not in self._RELATION_TYPES:
            raise ConflictError(f"unsupported relation: {relation}", code="bad_relation")
        if not from_id or not to_id or from_id == to_id:
            raise ConflictError("invalid from_id/to_id", code="bad_ids")
        now = _now()
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO memory_relations(from_id, to_id, relation, note, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (from_id, to_id, rel, note or "", now),
            )
            rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return {
            "ok": True,
            "id": rid,
            "from_id": from_id,
            "to_id": to_id,
            "relation": rel,
            "note": note or "",
            "confidence": confidence,
            "metadata": metadata or {},
            "created_at": now,
        }

    def list_relations(self, memory_id: str, *, limit: int = 40) -> list[dict[str, Any]]:
        lim = max(1, min(200, int(limit or 40)))
        rows = self.db.connect().execute(
            """
            SELECT id, from_id, to_id, relation, note, created_at
            FROM memory_relations
            WHERE from_id=? OR to_id=?
            ORDER BY id DESC LIMIT ?
            """,
            (memory_id, memory_id, lim),
        ).fetchall()
        return [dict(r) for r in rows]

    def store_change_plan(self, plan: dict[str, Any]) -> str:
        now = _now()
        pid = str(plan.get("change_id") or new_id("cpl"))
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO change_plans(
                  id, observation_id, change_type, risk_level, confidence,
                  approval_requirement, execution_status, verification_status,
                  payload_json, rollback_reference, created_at, updated_at, applied_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pid,
                    plan.get("observation_id"),
                    str(plan.get("change_type") or "NO_CHANGE"),
                    str(plan.get("risk_level") or "medium"),
                    float(plan.get("confidence") or 0),
                    str(plan.get("approval_requirement") or "human"),
                    str(plan.get("execution_status") or "proposed"),
                    str(plan.get("verification_status") or "pending"),
                    json.dumps(plan, ensure_ascii=False),
                    plan.get("rollback_reference"),
                    now,
                    now,
                    None,
                ),
            )
        return pid

    def get_change_plan(self, plan_id: str) -> dict[str, Any] | None:
        row = self.db.connect().execute(
            "SELECT * FROM change_plans WHERE id=?", (plan_id,)
        ).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        payload.update(
            {
                "change_id": row["id"],
                "observation_id": row["observation_id"],
                "change_type": row["change_type"],
                "risk_level": row["risk_level"],
                "confidence": row["confidence"],
                "approval_requirement": row["approval_requirement"],
                "execution_status": row["execution_status"],
                "verification_status": row["verification_status"],
                "rollback_reference": row["rollback_reference"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "applied_at": row["applied_at"],
            }
        )
        return payload

    def list_change_plans(
        self, *, limit: int = 40, execution_status: str | None = None
    ) -> list[dict[str, Any]]:
        lim = max(1, min(200, int(limit or 40)))
        sql = "SELECT id FROM change_plans WHERE 1=1"
        args: list[Any] = []
        if execution_status:
            sql += " AND execution_status=?"
            args.append(execution_status)
        sql += " ORDER BY created_at DESC LIMIT ?"
        args.append(lim)
        rows = self.db.connect().execute(sql, tuple(args)).fetchall()
        out = []
        for r in rows:
            p = self.get_change_plan(str(r["id"]))
            if p:
                out.append(p)
        return out

    def update_change_plan(
        self,
        plan_id: str,
        *,
        execution_status: str | None = None,
        verification_status: str | None = None,
        rollback_reference: str | None = None,
        payload_patch: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        cur = self.get_change_plan(plan_id)
        if not cur:
            return None
        if payload_patch:
            cur.update(payload_patch)
        now = _now()
        exec_s = execution_status or cur.get("execution_status")
        ver_s = verification_status or cur.get("verification_status")
        rb = rollback_reference if rollback_reference is not None else cur.get("rollback_reference")
        applied_at = now if exec_s == "applied" else cur.get("applied_at")
        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE change_plans SET
                  execution_status=?, verification_status=?, rollback_reference=?,
                  payload_json=?, updated_at=?, applied_at=?
                WHERE id=?
                """,
                (exec_s, ver_s, rb, json.dumps(cur, ensure_ascii=False), now, applied_at, plan_id),
            )
        return self.get_change_plan(plan_id)

    def store_cognitive_schema(self, schema: dict[str, Any]) -> str:
        now = _now()
        sid = str(schema.get("id") or new_id("sch"))
        name = str(schema.get("name") or "未命名图式").strip() or "未命名图式"
        description = str(schema.get("description") or "")
        schema_type = str(schema.get("type") or schema.get("schema_type") or "KNOWLEDGE")
        state = str(schema.get("state") or "PROPOSED").upper()
        confidence = float(schema.get("confidence") or 0.4)
        version = int(schema.get("version") or 1)
        payload = dict(schema)
        payload.update(
            {
                "id": sid,
                "type": schema_type,
                "state": state,
                "confidence": confidence,
                "version": version,
                "created_at": payload.get("created_at") or now,
                "updated_at": now,
            }
        )
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO cognitive_schemas(
                  id, name, description, schema_type, state, confidence,
                  version, payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  name=excluded.name, description=excluded.description,
                  schema_type=excluded.schema_type, state=excluded.state,
                  confidence=excluded.confidence, version=excluded.version,
                  payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """,
                (
                    sid, name, description, schema_type, state, confidence, version,
                    json.dumps(payload, ensure_ascii=False),
                    payload.get("created_at") or now, now,
                ),
            )
            conn.execute(
                """
                INSERT INTO schema_versions(
                  id, schema_id, version, change_type, reason, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("sv"), sid, version,
                    str(schema.get("change_type") or "CREATE"),
                    str(schema.get("reason") or "store"),
                    json.dumps(payload, ensure_ascii=False), now,
                ),
            )
        return sid

    def get_cognitive_schema(self, schema_id: str) -> dict[str, Any] | None:
        row = self.db.connect().execute(
            "SELECT * FROM cognitive_schemas WHERE id=?", (schema_id,)
        ).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        payload.update(
            {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "type": row["schema_type"],
                "schema_type": row["schema_type"],
                "state": row["state"],
                "confidence": row["confidence"],
                "version": row["version"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
        return payload

    def list_cognitive_schemas(
        self, *, limit: int = 40, state: str | None = None, schema_type: str | None = None
    ) -> list[dict[str, Any]]:
        lim = max(1, min(200, int(limit or 40)))
        sql = "SELECT id FROM cognitive_schemas WHERE 1=1"
        args: list[Any] = []
        if state:
            sql += " AND state=?"
            args.append(str(state).upper())
        if schema_type:
            sql += " AND schema_type=?"
            args.append(schema_type)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        args.append(lim)
        rows = self.db.connect().execute(sql, tuple(args)).fetchall()
        out = []
        for r in rows:
            s = self.get_cognitive_schema(str(r["id"]))
            if s:
                out.append(s)
        return out

    def update_cognitive_schema(
        self,
        schema_id: str,
        *,
        patch: dict[str, Any] | None = None,
        state: str | None = None,
        change_type: str = "REFINE",
        reason: str = "",
    ) -> dict[str, Any] | None:
        cur = self.get_cognitive_schema(schema_id)
        if not cur:
            return None
        now = _now()
        if patch:
            cur.update(patch)
        if state:
            cur["state"] = str(state).upper()
        cur["version"] = int(cur.get("version") or 1) + 1
        cur["updated_at"] = now
        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE cognitive_schemas SET
                  name=?, description=?, schema_type=?, state=?, confidence=?,
                  version=?, payload_json=?, updated_at=?
                WHERE id=?
                """,
                (
                    str(cur.get("name") or ""),
                    str(cur.get("description") or ""),
                    str(cur.get("type") or cur.get("schema_type") or "KNOWLEDGE"),
                    str(cur.get("state") or "PROPOSED"),
                    float(cur.get("confidence") or 0.4),
                    int(cur["version"]),
                    json.dumps(cur, ensure_ascii=False),
                    now,
                    schema_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO schema_versions(
                  id, schema_id, version, change_type, reason, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("sv"), schema_id, int(cur["version"]), change_type,
                    reason or change_type, json.dumps(cur, ensure_ascii=False), now,
                ),
            )
        return self.get_cognitive_schema(schema_id)

    def store_cognitive_change_plan(self, plan: dict[str, Any]) -> str:
        now = _now()
        pid = str(plan.get("id") or new_id("ccp"))
        payload = dict(plan)
        payload["id"] = pid
        payload.setdefault("created_at", now)
        payload["updated_at"] = now
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO cognitive_change_plans(
                  id, operation, risk_level, approval_required, status,
                  payload_json, created_at, updated_at, applied_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pid,
                    str(plan.get("operation") or "UPDATE"),
                    str(plan.get("riskLevel") or plan.get("risk_level") or "MEDIUM"),
                    1 if plan.get("approvalRequired", plan.get("approval_required", True)) else 0,
                    str(plan.get("status") or "PROPOSED"),
                    json.dumps(payload, ensure_ascii=False),
                    payload.get("created_at") or now,
                    now,
                    None,
                ),
            )
        return pid

    def get_cognitive_change_plan(self, plan_id: str) -> dict[str, Any] | None:
        row = self.db.connect().execute(
            "SELECT * FROM cognitive_change_plans WHERE id=?", (plan_id,)
        ).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        payload.update(
            {
                "id": row["id"],
                "operation": row["operation"],
                "risk_level": row["risk_level"],
                "approval_required": bool(row["approval_required"]),
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "applied_at": row["applied_at"],
            }
        )
        return payload

    def list_cognitive_change_plans(
        self, *, limit: int = 40, status: str | None = None
    ) -> list[dict[str, Any]]:
        lim = max(1, min(200, int(limit or 40)))
        sql = "SELECT id FROM cognitive_change_plans WHERE 1=1"
        args: list[Any] = []
        if status:
            sql += " AND status=?"
            args.append(str(status).upper())
        sql += " ORDER BY created_at DESC LIMIT ?"
        args.append(lim)
        rows = self.db.connect().execute(sql, tuple(args)).fetchall()
        out = []
        for r in rows:
            p = self.get_cognitive_change_plan(str(r["id"]))
            if p:
                out.append(p)
        return out

    def update_cognitive_change_plan(
        self,
        plan_id: str,
        *,
        status: str | None = None,
        payload_patch: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        cur = self.get_cognitive_change_plan(plan_id)
        if not cur:
            return None
        now = _now()
        if payload_patch:
            cur.update(payload_patch)
        st = str(status or cur.get("status") or "PROPOSED").upper()
        cur["status"] = st
        cur["updated_at"] = now
        applied_at = now if st == "APPLIED" else cur.get("applied_at")
        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE cognitive_change_plans SET
                  status=?, payload_json=?, updated_at=?, applied_at=?
                WHERE id=?
                """,
                (st, json.dumps(cur, ensure_ascii=False), now, applied_at, plan_id),
            )
        return self.get_cognitive_change_plan(plan_id)

    def count_cognitive_schemas(self) -> int:
        try:
            row = self.db.connect().execute(
                "SELECT COUNT(*) AS n FROM cognitive_schemas"
            ).fetchone()
            return int(row["n"] if row else 0)
        except sqlite3.OperationalError:
            return 0
