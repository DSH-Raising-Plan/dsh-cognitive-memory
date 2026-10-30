# Changelog

## 0.3.1 — P0 Safety Hardening

- 进程锁：`storage/process_lock.py`（同 `data_dir` 独占；OS 文件锁）
- 备份 bundle：`manifest.json` + SHA-256；SQLite Backup API 恢复
- 迁移：preflight / 升级前自动备份 / integrity + schema 校验
- 删除：Observation DELETE、Hard Forget 清 versions/relations/schema refs、取消相关 tasks
- REST：`/privacy/deletion-plan|execute`、`POST /memories/{id}/forget`
- CLI：`mnemosyne doctor`；文档 Implemented/Partial/Planned + `MNEMOSYNE_2.0_FINAL_PLAN.md`

## 0.3.0 — Mnemosyne 2.0 P0–P1 回灌

- **MNE-P0-01** `POST /api/v1/retrieve`：RetrievalPlanner + FOUND/PARTIAL/NO_MATCH/FAILED/NOT_NEEDED；工具 `memory_retrieve`
- **MNE-P0-02** 耐久观察队列 `src/capture-queue.js`（JSONL）；`session_id` 检索过滤
- **MNE-P0-03** ChangeDetect / ChangePlan apply·rollback；`memory_relations` 写入 API
- **MNE-P1-01** Capability Gate 默认 LOCKED；`/capabilities*`；RL/Value 执行入口硬锁
- **MNE-P1-02** CognitiveSchema 发现/同化/顺应（引用 memory_id，不另建 LT）
- **MNE-P1-03** metacognition reflect / impact stub
- **MNE-P2-01** RL-A / V-A stub（训练与高级价值仍 LOCKED）
- 迁移 `002_change_plan_schema_gate`

## 0.1.0

- V1.0 工程骨架：FastAPI REST、`MemoryService`、SQLite 迁移、FTS5
- Outbox / Inbox / Tasks 后台调度；规则版情节归纳与候选晋升
- MCP stdio 工具与 REST 共用同一业务核心
- DSH 插件 `dsh-mnemosyne`：子进程托管 + 工具注册
