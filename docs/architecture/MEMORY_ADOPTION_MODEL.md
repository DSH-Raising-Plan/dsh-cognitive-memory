# Memory Adoption Model（草案）

> **轨 B / 里程碑 M-E** · 可与 M-A～M-D **同步设计**，**不要求**在 E2E 迁移前实现。  
> **目标：** 定义何时、如何将「已迁移数据」提升为 Agent 的权威记忆来源。

## 核心问题

1. 迁移完成后，谁是权威（source of truth）？  
2. 旧 Agent / 旧库如何只读兼容？  
3. 切换是否可逆？如何审计？

## 建议原则

| 原则 | 说明 |
| --- | --- |
| 迁移 ≠ 接管 | Staging/Commit 到 Observation/Evidence 后，默认仍非 Active |
| 显式切换 | Adoption 需要用户或运维确认步骤 |
| Bridge 优先 | 先提供只读 Bridge / 投影，再谈写路径切换 |
| 可回退 | 保留旧权威指针与切换日志 |
| 不自动退役 | 旧库删除/退役单独高风险流程（暂缓） |

## 概念阶段（设计）

```
Imported (staging/verified)
  → Bridged (可读投影，权威仍在旧侧或双读)
  → Adopted (Mnemosyne 为权威写路径)
  → (可选) Legacy Read-only
```

## 与迁移引擎边界

| Adoption | Migration |
| --- | --- |
| 权威来源、切换策略、Bridge | Preview / Plan / Staging / Commit |
| Agent 配置与兼容接口 | Provider 提取与校验 |

## 非目标（当前）

- 自动切换旧 Agent  
- 完整 Compatibility Gateway 实现  
- 双向同步  

详见 [`MEMORY_COMPATIBILITY_ARCHITECTURE.md`](./MEMORY_COMPATIBILITY_ARCHITECTURE.md)。
