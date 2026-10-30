# Mnemosyne 2.0 回灌说明（本仓库）

分支：`feat/mnemosyne-2.0-p0-p1`

对照 T0 `COMPOSER_TASKS.md`：

| Task | 状态 |
| --- | --- |
| MNE-P0-01 RetrievalPlanner + `/retrieve` | ✅ |
| MNE-P0-02 Durable capture + session filter | ✅ |
| MNE-P0-03 ChangePlan + relations | ✅ |
| MNE-P1-01 Capability Gate | ✅ 默认 LOCKED |
| MNE-P1-02 Schema Engine MVP | ✅ PROPOSED 候选 |
| MNE-P1-03 Metacognition stub | ✅ |
| MNE-P2-01 RL/V stubs | ✅ 硬锁 |

原则：单一 LT（本服务 SQLite）；Schema 只引用证据；Gate 不可 Agent 自改。
