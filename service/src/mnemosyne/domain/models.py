# -*- coding: utf-8 -*-
"""领域模型与枚举（与 SQLite / API 契约对齐）。"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryStatus(str, Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"


class SourceKind(str, Enum):
    USER_STATEMENT = "user_statement"
    DIALOG = "dialog"
    VIDEO_OBSERVATION = "video_observation"
    AGENT_INFERENCE = "agent_inference"
    SYSTEM = "system"
    FEEDBACK = "feedback"


class RelationKind(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DERIVES = "derives"
    SUPERSEDES = "supersedes"


class ObservationIn(BaseModel):
    source_kind: SourceKind
    content: str
    occurred_at: str | None = None
    producer: str = "dsh"
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_ref: str | None = None
    idempotency_key: str | None = None


class Observation(ObservationIn):
    id: str
    created_at: str


class MemoryProposeIn(BaseModel):
    type: MemoryType = MemoryType.SEMANTIC
    content: str
    source_ids: list[str] = Field(default_factory=list)
    status: MemoryStatus = MemoryStatus.CANDIDATE
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = None
    expires_at: str | None = None
    idempotency_key: str | None = None


class MemoryUpdateIn(BaseModel):
    content: str | None = None
    status: MemoryStatus | None = None
    metadata: dict[str, Any] | None = None
    confidence: float | None = None
    expires_at: str | None = None
    expected_version: int | None = None


class Memory(BaseModel):
    id: str
    type: MemoryType
    status: MemoryStatus
    content: str
    source_ids: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    last_confirmed_at: str | None = None
    version: int = 1
    confidence: float | None = None
    expires_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceLink(BaseModel):
    memory_id: str
    observation_id: str
    relation: RelationKind = RelationKind.SUPPORTS
    note: str = ""


class FeedbackIn(BaseModel):
    memory_id: str
    useful: bool | None = None
    incorrect: bool | None = None
    note: str = ""
    producer: str = "dsh.agent"


class SearchQuery(BaseModel):
    query: str = ""
    types: list[MemoryType] | None = None
    status: list[MemoryStatus] | None = None
    limit: int = 10
    include_evidence: bool = False


class ContextBuildIn(BaseModel):
    query: str
    token_budget: int | None = None
    types: list[MemoryType] | None = None
    limit: int = 12


class ContextBuildOut(BaseModel):
    fragments: list[dict[str, Any]]
    token_estimate: int
    brief: str


class TaskCreateIn(BaseModel):
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None


class Task(BaseModel):
    id: str
    task_type: str
    status: str
    payload: dict[str, Any] = Field(default_factory=dict)
    attempts: int = 0
    last_error: str = ""
    created_at: str
    updated_at: str


class MemoryRelationIn(BaseModel):
    from_id: str
    to_id: str
    relation: str
    note: str = ""
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrieveIn(BaseModel):
    """统一检索入口（含触发规划）。"""

    query: str = ""
    force: bool = False
    limit: int = 8
    mode: str = "current"
    token_budget: int | None = None
    types: list[MemoryType] | None = None
    session_id: str | None = None


class ChangeDetectIn(BaseModel):
    observation_id: str
    dry_run: bool = True


class ChangePlanBuildIn(BaseModel):
    observation_id: str
    dry_run: bool = True
    persist: bool = True


class ChangePlanApplyIn(BaseModel):
    confirm: bool = False


class SchemaDiscoverIn(BaseModel):
    limit_memories: int = 200
    min_cluster: int = 3
    min_similarity: float = 0.22
    persist: bool = True


class SchemaAssimilateIn(BaseModel):
    memory_ids: list[str] = Field(default_factory=list)
    note: str = ""


class SchemaAccommodateIn(BaseModel):
    memory_ids: list[str] = Field(default_factory=list)
    counter_note: str = ""
    propose_split: bool = True


class CognitiveChangePlanIn(BaseModel):
    operation: str = "UPDATE"
    target_schema_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    expected_impact: list[str] = Field(default_factory=list)
    risk_level: str = "MEDIUM"
    approval_required: bool = True
    reason: str = ""


class CognitiveChangePlanApplyIn(BaseModel):
    confirm: bool = False


class CapabilityCheckIn(BaseModel):
    capability: str


class CapabilitySetIn(BaseModel):
    capability: str
    level: str
    enabled: bool | None = None
    actor: str = "external_governance"


class ReflectionIn(BaseModel):
    judgment: str = ""
    schema_ids: list[str] = Field(default_factory=list)
    memory_ids: list[str] = Field(default_factory=list)


class ValueAnalyzeIn(BaseModel):
    intent: str
    stakeholders: list[str] = Field(default_factory=list)
    proposed_action: str = ""
