# Memory Compatibility Architecture（草案）

> **轨 B / Adoption 配套** · 回答「原有 Agent 如何继续用记忆」。  
> **暂缓实现**完整 Compatibility Gateway；本文只定边界与评估清单。

## 目标

在不破坏 Foundation 1.0 契约的前提下，为「旧运行时 ↔ Mnemosyne 记忆」提供兼容路径的**设计空间**。

## 分层

```
Legacy Agent / SDK
       │
       ▼
Compatibility Facade（设计中；非现网）
       │
       ├── Bridge Read（投影已导入记忆）
       ├── Write Policy（默认拒绝或仅 Observation）
       └── Mapping（外部 ID / 会话键）
       │
       ▼
Mnemosyne Service Contract（不变）
```

## 评估清单（进入实现前）

- [ ] 目标 Provider/Agent 的 API 语义是否文档化  
- [ ] 读路径是否可完全由 Bridge 覆盖  
- [ ] 写路径是否需要模拟旧 API（若需要 → 单独版本升级评估）  
- [ ] 是否引入与 PCIP/REST 冲突的新公共端点（默认否）  
- [ ] 失败时是否降级到只读 / 明确错误  

## 与 Foundation 硬约束

- **不得**静默改写 `foundation-0.1.0` REST / PCIP / Component Contract  
- 若必须扩展公共面：走兼容性评估 + **显式版本 bump**  
- 安全原则（Observation-only inbound、deny-by-default、component scopes）对 Facade 同样适用  

## 第二批候选

Zep / Graphiti、Letta 等 — **首批管线稳定后再评估** Adapter + Facade 语义。
