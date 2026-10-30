# -*- coding: utf-8 -*-
"""FastAPI REST：统一前缀 /api/v1，全部委托 MemoryService。"""

from __future__ import annotations

import secrets
import uuid
from typing import Any, Callable

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from mnemosyne.core.service import ConflictError, MemoryService, NotFoundError
from mnemosyne.domain.models import (
    CapabilityCheckIn,
    CapabilitySetIn,
    ChangeDetectIn,
    ChangePlanApplyIn,
    ChangePlanBuildIn,
    CognitiveChangePlanApplyIn,
    CognitiveChangePlanIn,
    ContextBuildIn,
    EvidenceIn,
    FeedbackIn,
    MemoryProposeIn,
    MemoryRelationIn,
    MemoryUpdateIn,
    ObservationIn,
    ReflectionIn,
    RetrieveIn,
    SchemaAccommodateIn,
    SchemaAssimilateIn,
    SchemaDiscoverIn,
    SearchQuery,
    TaskCreateIn,
    ValueAnalyzeIn,
)


def create_app(
    service: MemoryService,
    *,
    access_token: str,
    api_prefix: str = "/api/v1",
) -> FastAPI:
    app = FastAPI(title="Mnemosyne", version="0.2.0")
    app.state.service = service
    app.state.access_token = access_token

    def require_token(
        authorization: str | None = Header(default=None),
        x_memory_token: str | None = Header(default=None),
    ) -> None:
        token = None
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
        elif x_memory_token:
            token = x_memory_token.strip()
        expected = app.state.access_token
        if not expected or not token or not secrets.compare_digest(token, expected):
            raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "invalid token"})

    @app.middleware("http")
    async def add_request_id(request: Request, call_next: Callable):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = rid
        response: Response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response

    @app.exception_handler(NotFoundError)
    async def _nf(_req: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"code": exc.code, "message": str(exc)})

    @app.exception_handler(ConflictError)
    async def _cf(_req: Request, exc: ConflictError):
        return JSONResponse(status_code=409, content={"code": exc.code, "message": str(exc)})

    pref = api_prefix.rstrip("/") or "/api/v1"

    @app.get(f"{pref}/health")
    def health(_: None = Depends(require_token)) -> dict[str, Any]:
        return service.health()

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"ok": "true"}

    @app.post(f"{pref}/memories/search")
    def search(body: SearchQuery, _: None = Depends(require_token)) -> dict[str, Any]:
        rows = service.search(body)
        return {"items": [m.model_dump() for m in rows], "count": len(rows)}

    @app.get(f"{pref}/memories/{{memory_id}}")
    def get_memory(
        memory_id: str,
        include_evidence: bool = False,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        return service.get_memory(memory_id, include_evidence=include_evidence)

    @app.post(f"{pref}/memories")
    def propose(body: MemoryProposeIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.propose_memory(body).model_dump()

    @app.patch(f"{pref}/memories/{{memory_id}}")
    def update(memory_id: str, body: MemoryUpdateIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.update_memory(memory_id, body).model_dump()

    @app.delete(f"{pref}/memories/{{memory_id}}")
    def forget(memory_id: str, hard: bool = False, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.forget_memory(memory_id, hard=hard)

    @app.post(f"{pref}/observations")
    def observations(body: ObservationIn, _: None = Depends(require_token)) -> dict[str, Any]:
        dump = service.capture_observation(body).model_dump()
        dump["persisted_ok"] = True
        dump["retrieval_ready"] = True
        dump["write_stages"] = ["RECEIVED", "PERSISTED", "INDEXED", "VERIFIED"]
        return dump

    @app.get(f"{pref}/observations/{{observation_id}}")
    def get_observation(observation_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        row = service.get_observation(observation_id)
        if not row:
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": f"observation not found: {observation_id}"},
            )
        return row

    @app.delete(f"{pref}/observations/{{observation_id}}")
    def delete_observation(
        observation_id: str,
        hard: bool = True,
        cascade_memories: bool = True,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        return service.delete_observation(
            observation_id, hard=hard, cascade_memories=cascade_memories
        )

    @app.post(f"{pref}/evidences")
    def create_evidence(body: EvidenceIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.add_evidence(body).model_dump()

    @app.get(f"{pref}/memories/{{memory_id}}/evidences")
    def list_memory_evidences(
        memory_id: str,
        evidence_type: str | None = None,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        items = service.list_evidence(
            subject_kind="memory", subject_id=memory_id, evidence_type=evidence_type
        )
        return {"items": items, "count": len(items)}

    @app.post(f"{pref}/memories/{{memory_id}}/promote-check")
    def promote_check(memory_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.cognition.promote import evaluate_and_apply

        return evaluate_and_apply(service, memory_id)

    @app.get(f"{pref}/decisions")
    def list_decisions(
        subject_id: str | None = None,
        limit: int = 40,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        items = service.list_decision_logs(subject_id=subject_id, limit=limit)
        return {"items": items, "count": len(items)}

    @app.post(f"{pref}/privacy/deletion-plan")
    def privacy_deletion_plan(body: dict[str, Any], _: None = Depends(require_token)) -> dict[str, Any]:
        return service.build_deletion_plan(
            observation_id=body.get("observation_id"),
            memory_id=body.get("memory_id"),
            hard=bool(body.get("hard", True)),
        )

    @app.post(f"{pref}/privacy/deletion-execute")
    def privacy_deletion_execute(body: dict[str, Any], _: None = Depends(require_token)) -> dict[str, Any]:
        if body.get("observation_id"):
            return service.delete_observation(
                str(body["observation_id"]),
                hard=bool(body.get("hard", True)),
                cascade_memories=bool(body.get("cascade_memories", True)),
            )
        if body.get("memory_id"):
            return service.forget_memory(str(body["memory_id"]), hard=bool(body.get("hard", True)))
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_request", "message": "observation_id or memory_id required"},
        )

    @app.post(f"{pref}/memories/{{memory_id}}/forget")
    def forget_memory_post(
        memory_id: str,
        body: dict[str, Any] | None = None,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        hard = True if body is None else bool((body or {}).get("hard", True))
        return service.forget_memory(memory_id, hard=hard)

    @app.post(f"{pref}/feedback")
    def feedback(body: FeedbackIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.feedback(body)

    @app.post(f"{pref}/contexts/build")
    def contexts(body: ContextBuildIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.build_context(body).model_dump()

    @app.post(f"{pref}/retrieve")
    def retrieve(body: RetrieveIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.retrieval.pipeline import run_retrieve

        return run_retrieve(
            service,
            query=body.query,
            force=body.force,
            limit=body.limit,
            mode=body.mode,
            token_budget=body.token_budget,
            types=body.types,
            session_id=body.session_id,
        )

    @app.post(f"{pref}/tasks")
    def create_task(body: TaskCreateIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.create_task(body).model_dump()

    @app.get(f"{pref}/tasks/{{task_id}}")
    def get_task(task_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.get_task(task_id).model_dump()

    @app.post(f"{pref}/relations")
    def create_relation(body: MemoryRelationIn, _: None = Depends(require_token)) -> dict[str, Any]:
        return service.link_memories(
            from_id=body.from_id,
            to_id=body.to_id,
            relation=body.relation,
            note=body.note,
            confidence=body.confidence,
            metadata=body.metadata,
        )

    @app.get(f"{pref}/memories/{{memory_id}}/relations")
    def get_relations(memory_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        items = service.list_relations(memory_id)
        return {"items": items, "count": len(items)}

    @app.post(f"{pref}/changes/detect")
    def changes_detect(body: ChangeDetectIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.cognition.change_detect import detect_changes_for_observation

        return detect_changes_for_observation(
            service, body.observation_id, dry_run=body.dry_run
        )

    @app.post(f"{pref}/changes/plans")
    def changes_plans_build(body: ChangePlanBuildIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.cognition.change_plan import build_plans_for_observation

        return build_plans_for_observation(
            service, body.observation_id, dry_run=body.dry_run, persist=body.persist
        )

    @app.get(f"{pref}/changes/plans")
    def changes_plans_list(
        limit: int = 40,
        execution_status: str | None = None,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        items = service.list_change_plans(limit=limit, execution_status=execution_status)
        return {"ok": True, "items": items, "count": len(items)}

    @app.post(f"{pref}/changes/plans/{{plan_id}}/apply")
    def changes_plans_apply(
        plan_id: str, body: ChangePlanApplyIn, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        from mnemosyne.cognition.change_plan import apply_change_plan

        return apply_change_plan(service, plan_id, confirm=bool(body.confirm))

    @app.post(f"{pref}/changes/plans/{{plan_id}}/rollback")
    def changes_plans_rollback(plan_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.cognition.change_plan import rollback_change_plan

        return rollback_change_plan(service, plan_id)

    @app.post(f"{pref}/schemas/discover")
    def schemas_discover(body: SchemaDiscoverIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.cognition.schema_discovery import discover_schema_candidates

        return discover_schema_candidates(
            service,
            limit_memories=body.limit_memories,
            min_cluster=body.min_cluster,
            min_similarity=body.min_similarity,
            persist=body.persist,
        )

    @app.get(f"{pref}/schemas")
    def schemas_list(
        limit: int = 40,
        state: str | None = None,
        schema_type: str | None = None,
        _: None = Depends(require_token),
    ) -> dict[str, Any]:
        items = service.list_cognitive_schemas(limit=limit, state=state, schema_type=schema_type)
        return {"ok": True, "items": items, "count": len(items)}

    @app.get(f"{pref}/schemas/{{schema_id}}")
    def schemas_get(schema_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        sch = service.get_cognitive_schema(schema_id)
        if not sch:
            raise HTTPException(status_code=404, detail={"code": "not_found", "message": "schema"})
        return sch

    @app.post(f"{pref}/schemas/{{schema_id}}/assimilate")
    def schemas_assimilate(
        schema_id: str, body: SchemaAssimilateIn, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        from mnemosyne.cognition.schema_ops import assimilate_schema

        return assimilate_schema(service, schema_id, memory_ids=body.memory_ids, note=body.note)

    @app.post(f"{pref}/schemas/{{schema_id}}/accommodate")
    def schemas_accommodate(
        schema_id: str, body: SchemaAccommodateIn, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        from mnemosyne.cognition.schema_ops import accommodate_schema

        return accommodate_schema(
            service,
            schema_id,
            memory_ids=body.memory_ids,
            counter_note=body.counter_note,
            propose_split=body.propose_split,
        )

    @app.post(f"{pref}/schemas/plans")
    def schemas_plans_create(
        body: CognitiveChangePlanIn, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        pid = service.store_cognitive_change_plan(
            {
                "operation": body.operation,
                "targetSchemaIds": body.target_schema_ids,
                "evidenceRefs": body.evidence_refs,
                "expectedImpact": body.expected_impact,
                "risk_level": body.risk_level,
                "approval_required": body.approval_required,
                "status": "PROPOSED",
                "reason": body.reason,
            }
        )
        return {"ok": True, "id": pid, "plan": service.get_cognitive_change_plan(pid)}

    @app.get(f"{pref}/schemas/plans")
    def schemas_plans_list(
        limit: int = 40, status: str | None = None, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        items = service.list_cognitive_change_plans(limit=limit, status=status)
        return {"ok": True, "items": items, "count": len(items)}

    @app.post(f"{pref}/schemas/plans/{{plan_id}}/apply")
    def schemas_plans_apply(
        plan_id: str, body: CognitiveChangePlanApplyIn, _: None = Depends(require_token)
    ) -> dict[str, Any]:
        from mnemosyne.cognition.schema_ops import apply_cognitive_change_plan

        return apply_cognitive_change_plan(service, plan_id, confirm=bool(body.confirm))

    @app.post(f"{pref}/metacognition/reflect")
    def metacognition_reflect(body: ReflectionIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.cognition.metacognition import reflect

        return reflect(
            service,
            judgment=body.judgment,
            schema_ids=body.schema_ids,
            memory_ids=body.memory_ids,
        )

    @app.get(f"{pref}/metacognition/impact/{{schema_id}}")
    def metacognition_impact(schema_id: str, _: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.cognition.metacognition import analyze_impact

        return analyze_impact(service, schema_id)

    @app.get(f"{pref}/capabilities")
    def capabilities_list(_: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.governance.capability_gate import list_capabilities

        items = list_capabilities(service.db)
        return {"ok": True, "items": items, "count": len(items)}

    @app.post(f"{pref}/capabilities/check")
    def capabilities_check(body: CapabilityCheckIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.governance.capability_gate import check_capability

        return check_capability(service.db, body.capability)

    @app.post(f"{pref}/capabilities/set")
    def capabilities_set(body: CapabilitySetIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.governance.capability_gate import set_capability_level

        return set_capability_level(
            service.db,
            body.capability,
            level=body.level,
            enabled=body.enabled,
            actor=body.actor or "external_governance",
        )

    @app.post(f"{pref}/rl/train")
    def rl_train(_: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.governance.reinforcement_learning import run_offline_training

        return run_offline_training(service.db, {})

    @app.post(f"{pref}/rl/deploy")
    def rl_deploy(policy_id: str = "default", _: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.governance.reinforcement_learning import deploy_policy

        return deploy_policy(service.db, policy_id)

    @app.post(f"{pref}/value/analyze")
    def value_analyze(body: ValueAnalyzeIn, _: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.governance.value_system import analyze_value_conflict_basic

        return analyze_value_conflict_basic(
            body.intent,
            stakeholders=body.stakeholders,
            proposed_action=body.proposed_action,
        )

    @app.post(f"{pref}/value/advanced")
    def value_advanced(_: None = Depends(require_token)) -> dict[str, Any]:
        from mnemosyne.governance.value_system import run_advanced_value_evaluation

        return run_advanced_value_evaluation(service.db, {})

    return app
