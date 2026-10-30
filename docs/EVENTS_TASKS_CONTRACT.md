# Events / Outbox / Tasks 职责契约

> 成熟度：**Implemented**（方案 A，与 [MNEMOSYNE_2.0_FINAL_PLAN.md](./MNEMOSYNE_2.0_FINAL_PLAN.md) 阶段 2 §5.5 对齐）

| 组件 | 职责 | 非职责 |
| --- | --- | --- |
| **Event** | 记录「发生了什么」（审计 / 可重放元数据） | 不直接执行认知业务 |
| **Outbox** | 至少一次把 Event 投递到本地总线 / 未来外部消费者 | 不等于业务已处理 |
| **Inbox** | 消费幂等去重 | — |
| **Task** | **正式业务执行路径**（consolidation / promote_check / review…） | — |
| **Dispatcher** | 调度 Outbox 投递 + 拉取 pending Tasks | — |
| **EventBus** | 进程内 pub/sub 基础设施 | 当前默认无业务订阅者 |
| **Decision Log** | 记录晋升等认知判断依据 | 不替代 Task |

## 写入约定

业务写路径在同一 SQLite 事务内：

1. 持久化 Observation / Memory / Evidence 等；
2. `_emit` → `events` + `outbox(pending)`；
3. 需要后台工作时 `_create_task` → `tasks(pending)`。

## 消费约定

- 认知处理以 **Task handler** 为准（见 `jobs/dispatcher.py`）。
- Outbox 成功标记 `delivered` 只表示事件已交给本地总线；**没有订阅者不代表失败**。
- 未来若引入真正的事件驱动 Consumer，须通过明确 Consumer Contract 注册，禁止模块随意 `subscribe`。

## 与删除的交互

资源删除后须取消相关 `pending/running` Tasks，防止异步路径复活已遗忘内容（P0 Safety）。
