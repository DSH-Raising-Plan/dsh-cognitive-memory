# DSH 外置认知记忆系统 — 总体技术方案（落地索引）

> 架构版本 **V1.0** · 代码位置：`services/cognitive-memory` + `_dsh_plugins/dsh-cognitive-memory`  
> 目标：**完全代替** 进程内 A-MEM（`Murasame/a_mem_bridge.py` + Chroma）。

本文是立项与开发拆分的**落地索引**；原则与接口以实现代码与 OpenAPI 为准。

**文档地图**

| 文档 | 内容 |
| --- | --- |
| [`../services/cognitive-memory/README.md`](../services/cognitive-memory/README.md) | 愿景、拟人化价值、结构选型 |
| [`COGNITIVE_MEMORY_ROADMAP.md`](./COGNITIVE_MEMORY_ROADMAP.md) | 算法优化清单、借鉴项目、P0–P3 排期 |
| [`COGNITIVE_MEMORY_STATE_MACHINE.md`](./COGNITIVE_MEMORY_STATE_MACHINE.md) | 状态机、证据分层、冲突/衰减、验收测试 |

核心链路：`原始事件 → 短期缓冲 → 事件关联 → 情节 → 行为模式 → 筛选 → 长期记忆 → 用户模型`  
视频：`runStoryboard → 片段 → 主题/实体 → 临时记忆 → 跨来源兴趣 → 长期记忆`

**六问（优化焦点，而非继续加层）：** 值得记什么？如何组成经历？何种证据够晋升？冲突如何更新？如何改善对话行为？如何证明有效？

## 目标摘要

独立记忆子进程，双通道：

- **快速**：工作记忆、即时检索、上下文构建（不阻塞对话）。
- **慢速**：情节归纳、兴趣候选、冲突/晋升、反馈修正（Outbox + Tasks 可恢复）。

底线：观察≠记忆、推断≠事实、事件可恢复、检索可降级、MCP/REST 共用一个 `MemoryService`。

图谱（P1 拟接 Graphiti）负责时间关系与混合检索；**心理学状态机**负责准入 / 证据 / 晋升 / 衰减 / 纠错。

## 仓库布局

```
services/cognitive-memory/          # Python FastAPI + SQLite 服务
_dsh_plugins/dsh-cognitive-memory/  # Node Host Adapter（子进程 + DSH tools）
docs/COGNITIVE_MEMORY_SPEC.md       # 本索引
docs/COGNITIVE_MEMORY_ROADMAP.md    # 优化清单与排期
docs/COGNITIVE_MEMORY_STATE_MACHINE.md  # 状态机规格草案
```

数据目录（不进仓库）：`%LOCALAPPDATA%/DSH/cognitive-memory/`

## 实施阶段对照

| 阶段 | 状态（V0.1 骨架） |
| --- | --- |
| 1 工程骨架 · 健康检查 · 子进程 | ✅ REST `/health` · `MemoryProcessHost` |
| 2 CRUD · 版本 · 幂等 | ✅ `MemoryService` |
| 3 Outbox / Inbox / Tasks | ✅ `BackgroundRuntime` |
| 4 FTS5 · contexts/build | ✅ 可降级 LIKE |
| 5 认知流水线 | ✅ 规则版 consolidate / promote（可换 LLM） |
| 6 桌宠对话闭环 | ✅ `cognitive_memory_bridge` + orchestrator / gatekeeper |
| 7 迁移备份恢复测试 | ✅ `cli backup/restore` + `tests/recovery` |
| 8 管理后台 / A-MEM 迁移 | ✅ 面板 + `migrate-amem` / `scripts/migrate_amem_to_cognitive.py` |
| 9 视频观察 → observation | ✅ `episode_write` → `submit_video_observation` |
| 10 状态机 + 证据规则（P0） | ⏳ 见 STATE_MACHINE 草案 |
| 11 Graphiti 混合检索（P1） | ⏳ |
| 12 兴趣证据分层与晋升（P2） | ⏳ |
| 13 空闲巩固与算法实验（P3） | ⏳ |

## 桌宠接入（已落地）

1. `Murasame/cognitive_memory_bridge.py`：HTTP 客户端，可 `auto_start` 拉起子进程。
2. `memory_orchestrator`：默认 retrieval/persist 首位为 `cognitive_memory`；`replace_a_mem=true` 时跳过 A-MEM 读写。
3. `gatekeeper_memory`：优先 `contexts/build`；无命中/未启用时才回退 A-MEM。
4. `config.json` / `config.example.json`：`cognitive_memory.enable=true`，`a_mem.enable=false`。
5. 管理后台「外置认知记忆」面板：`/api/cognitive-memory/*`。
6. 运维：`python -m cognitive_memory.cli backup|restore|migrate-amem`。

## 相关文档

- 现状记忆总图（含 A-MEM）：[MEMORY_MAP.md](./MEMORY_MAP.md)
- 算法优化与借鉴：[COGNITIVE_MEMORY_ROADMAP.md](./COGNITIVE_MEMORY_ROADMAP.md)
- 状态机与证据规范：[COGNITIVE_MEMORY_STATE_MACHINE.md](./COGNITIVE_MEMORY_STATE_MACHINE.md)
- A-MEM 标记为 **deprecated**，新写入已切到本服务。
