# Memory Migration Architecture（草案）

> **轨 B / Workstream 2** · 分支建议：`design/memory-migration`  
> **依赖：** [`MEMORY_INTERCHANGE_MODEL.md`](./MEMORY_INTERCHANGE_MODEL.md) 契约稳定后，Adapter 才正式实现。  
> **硬规则：** 不直写核心库；不覆盖已有记忆；不自动 Active；保留来源；可回滚。

## 生命周期

```
Discover → Extract → Map(Interchange) → Preview → Plan
    → Staging → Validate → Commit | Rollback
```

| 阶段 | 职责 |
| --- | --- |
| Discover | 用户指定 Provider + 位置；不做全盘自动扫描 |
| Extract | Provider Adapter 读取源数据 |
| Map | 转为 Memory Interchange Bundle |
| Preview | 人类可读摘要：条数、冲突、丢失字段 |
| Plan | 批次、冲突策略、幂等键 |
| Staging | 隔离暂存区（非核心 Active 表） |
| Validate | 完整性、对照、抽样 reconciliation |
| Commit | 经 Service Contract 写入 Observation/Evidence 路径 |
| Rollback / Resume | 按 batch_id 恢复 |

## 模块边界

```
migration/
├── providers/      # registry · adapters（实现属 Workstream 3）
├── extraction/
├── interchange/    # schema · mapper
├── planning/       # preview · planner · conflict_detector
├── execution/      # staging · batch_manager · executor
├── validation/
└── recovery/
```

## 与 Foundation 的接口

| 允许 | 禁止 |
| --- | --- |
| 调用已发布 REST / SDK（Observation 等） | 修改 Foundation REST/PCIP/Component 契约 |
| 将外源落为 Observation + provenance | 直接 INSERT 核心 memory 表 |
| Staging 使用独立存储/前缀 | 覆盖用户已有记忆 ID |

## 第一阶段范围

发现 → 读取 → 预览 → 计划 → Staging → 校验 → 提交/回滚。

**不做：** 自动切换 Agent、双向同步、自动退役旧库。

## 验收（设计层）

- [ ] 生命周期与失败模式文档化  
- [ ] Staging / Commit / Rollback 职责清晰  
- [ ] 与 Interchange Schema 字段对齐  
- [ ] 明确「Commit = Service Contract 写入」而非 DB 直写  
