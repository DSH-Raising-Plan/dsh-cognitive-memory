# Mnemosyne 2.0 回灌说明（本仓库）

分支基线：`feat/mnemosyne-2.0-p0-p1`（PR #13 · `9295d03`）  
后续安全加固：`feat/mnemosyne-2.0-p0-safety-hardening`  
最终路线：[MNEMOSYNE_2.0_FINAL_PLAN.md](./MNEMOSYNE_2.0_FINAL_PLAN.md)

对照 T0 `COMPOSER_TASKS.md`（功能 MVP；**不等于** Safe Upgrade Candidate）：

| Task | 成熟度 | 说明 |
| --- | --- | --- |
| MNE-P0-01 RetrievalPlanner + `/retrieve` | Implemented | 有单测 |
| MNE-P0-02 Durable capture + session filter | Implemented | Host JSONL queue + 测 |
| MNE-P0-03 ChangePlan + relations | Implemented | 规则版 |
| MNE-P1-01 Capability Gate | Implemented | 默认 LOCKED |
| MNE-P1-02 Schema Engine MVP | Partial | PROPOSED 候选；非完整证据引擎 |
| MNE-P1-03 Metacognition stub | Partial | stub |
| MNE-P2-01 RL/V stubs | Partial | 硬锁 stub |
| 进程锁 / 备份 round-trip / 删除级联 | Partial→进行中 | 阶段 1 P0 Safety |
| 完整状态机 / 正式 MCP / 真 DSH E2E | Planned | 阶段 2–3 |

原则：单一 LT（本服务 SQLite）；Schema 只引用证据；Gate 不可 Agent 自改。  
**Outbox 投递 ≠ 业务已消费**；当前正式业务执行路径是 **Tasks**。
