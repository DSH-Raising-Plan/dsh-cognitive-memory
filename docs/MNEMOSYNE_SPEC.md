# DSH 外置演化记忆系统 — 总体技术方案（落地索引）

> 架构版本 **V1.0 / Mnemosyne 2.0 MVP** · 本仓库布局：`service/`（Python）+ `src/`（DSH Host Adapter）  
> 状态约定：`Implemented` = 代码+测试；`Partial` = 有路径但有限制；`Planned` = 仅设计。  
> 最终路线：[MNEMOSYNE_2.0_FINAL_PLAN.md](./MNEMOSYNE_2.0_FINAL_PLAN.md) · 基线 PR #13 · 当前开发：P0 Safety Hardening。

本文是立项与开发拆分的**落地索引**；原则与接口以实现代码与 OpenAPI 为准。**不得将 Planned 描述为 Implemented。**

**文档地图**

| 文档 | 内容 | 成熟度 |
| --- | --- | --- |
| [MNEMOSYNE_2.0_FINAL_PLAN.md](./MNEMOSYNE_2.0_FINAL_PLAN.md) | 2.0 最终实施方案与阶段门槛 | Implemented（计划文档） |
| [MNEMOSYNE_ROADMAP.md](./MNEMOSYNE_ROADMAP.md) / 根 [`ROADMAP.md`](../ROADMAP.md) | 算法优化清单、借鉴项目 | Partial（愿景+排期；多项 Planned） |
| [MNEMOSYNE_STATE_MACHINE.md](./MNEMOSYNE_STATE_MACHINE.md) | 状态机、证据分层规格 | **Partial / 超前于代码** |
| [TRIAL.md](../TRIAL.md) | 试用与转正门槛 | Partial |

核心链路：`原始事件 → 短期缓冲 → 事件关联 → 情节 → 行为模式 → 筛选 → 长期记忆 → 用户模型`  
视频：`runStoryboard → 片段 → 主题/实体 → 临时记忆 → 跨来源兴趣 → 长期记忆`

**六问（优化焦点，而非继续加层）：** 值得记什么？如何组成经历？何种证据够晋升？冲突如何更新？如何改善对话行为？如何证明有效？

## 目标摘要

独立记忆子进程，双通道：

- **快速**：工作记忆、即时检索、上下文构建（不阻塞对话）。
- **慢速**：情节归纳、兴趣候选、冲突/晋升、反馈修正（Outbox + Tasks 可恢复）。

底线：观察≠记忆、推断≠事实、事件可恢复、检索可降级、MCP/REST 共用一个 `MemoryService`。

图谱（P1 拟接 Graphiti）负责时间关系与混合检索；**心理学状态机**负责准入 / 证据 / 晋升 / 衰减 / 纠错。

## 仓库布局（本仓库 · Implemented）

```
service/                     # Python FastAPI + SQLite（包名 mnemosyne）
src/                         # Node Host Adapter（子进程 + DSH tools）
docs/MNEMOSYNE_SPEC.md       # 本索引
docs/MNEMOSYNE_STATE_MACHINE.md
docs/MNEMOSYNE_2.0_FINAL_PLAN.md
```

数据目录（不进仓库）：`%LOCALAPPDATA%/DSH/mnemosyne/`（可用 `DSH_MNEMOSYNE_DATA_DIR` 覆盖）

## 实施阶段对照（相对 PR #13 / 2.0 MVP）

| 阶段 | 成熟度 | 说明 |
| --- | --- | --- |
| 工程骨架 · 健康检查 · 子进程 | Implemented | REST `/health` · `MemoryProcessHost` |
| CRUD · 版本 · 幂等 | Implemented | `MemoryService` |
| Outbox / Inbox / Tasks | Partial | 表+调度+恢复测有；**EventBus 无业务订阅者**；Tasks 才是业务执行 |
| FTS5 · contexts/build · retrieve | Implemented | 可降级 LIKE；RetrievalPlanner Partial→有测 |
| 认知流水线 | Partial | 规则版 consolidate / promote（非完整状态机） |
| DSH 自动捕获 | Partial | Host auto-capture + durable queue；真 E2E Planned |
| 迁移备份恢复 | Partial | CLI 有；完整 round-trip / 升级前备份 = P0 进行中 |
| 进程锁 · 删除级联 | Partial / 进行中 | P0 Safety Hardening |
| 状态机 + 证据规则 | Planned→Partial | 文档超前；代码仅 4 态 MemoryStatus |
| 正式 MCP SDK | Planned | 当前为自研 JSON-RPC 桩（Partial） |
| Graphiti / 兴趣分层 / PCIP | Planned | |

## DSH 接入（本仓库 Host · Partial）

1. `src/index.js`：`MemoryProcessHost` + tools + `auto_capture`。
2. 转正门槛与试用说明见根目录 [TRIAL.md](../TRIAL.md)。

**尚未验收（不能当主记忆）：** 真实对话闭环、零配置安装现场验证、Safe Upgrade Candidate、一周无丢/串。

## 相关文档

- 最终方案：[MNEMOSYNE_2.0_FINAL_PLAN.md](./MNEMOSYNE_2.0_FINAL_PLAN.md)
- 算法优化：[MNEMOSYNE_ROADMAP.md](./MNEMOSYNE_ROADMAP.md)
- 状态机规格（多为 Planned）：[MNEMOSYNE_STATE_MACHINE.md](./MNEMOSYNE_STATE_MACHINE.md)
- 试用 / 转正：[TRIAL.md](../TRIAL.md)
