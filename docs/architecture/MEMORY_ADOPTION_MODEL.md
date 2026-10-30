# Memory Adoption Model

> **轨 B / 里程碑 M-E Accepted（设计冻结；实现不挡迁移引擎）**  
> **目标：** 定义何时、如何将「已迁移数据」提升为 Agent 的权威记忆来源。

## 核心问题

1. 迁移完成后，谁是权威（source of truth）？  
2. 旧 Agent / 旧库如何只读兼容？  
3. 切换是否可逆？如何审计？

## 原则

| 原则 | 说明 |
| --- | --- |
| 迁移 ≠ 接管 | Commit 到 Observation/Evidence 后，默认仍非 Active |
| 显式切换 | Adoption 需要用户确认（CLI/Admin 勾选 + 审计日志） |
| Bridge 优先 | 先只读 Bridge / 投影，再谈写路径切换 |
| 可回退 | 保留旧权威指针与 `adoption_switch` 日志 |
| 不自动退役 | 旧库删除/退役单独高风险流程（暂缓） |

## 阶段状态机（设计）

```
Imported     Staging/Validate 通过；可 Commit
  → Observed   已经 Service Contract 写入 Observation/Evidence
  → Bridged    只读投影可供旧 Agent / 新运行时读取；权威写仍在旧侧或双读
  → Adopted    Mnemosyne 为权威写路径；旧侧只读或断开写
  → Legacy-RO  （可选）旧库只读归档
```

| 转移 | 触发 | 门禁 |
| --- | --- | --- |
| → Observed | Migration Commit | Validate 通过 |
| → Bridged | 用户启用 Bridge | 映射表完整；检索隔离 Active |
| → Adopted | 用户确认切换 | 抽样读取一致；写策略文档化；可回退演练 |
| → Legacy-RO | 用户确认 | Adopted 稳定期；**永不自动** |

## 权威来源记录（审计）

```json
{
  "subject": "user:alice",
  "authority": "mnemosyne|legacy|dual-read",
  "switched_at": "ISO-8601",
  "batch_ids": ["..."],
  "operator": "user|admin",
  "rollback_token": "opaque"
}
```

## Bridge 策略

| 模式 | 读 | 写 |
| --- | --- | --- |
| Legacy-primary | 旧库优先，Mnemosyne 补缺 | 仅旧库 |
| Dual-read | 合并去重（按 external_id） | 拒绝或仅 Observation |
| Mnemosyne-primary | Mnemosyne 优先 | 仅 Mnemosyne（Adopted） |

## 与迁移引擎边界

| Adoption | Migration |
| --- | --- |
| 权威来源、切换策略、Bridge | Preview / Plan / Staging / Commit |
| Agent 配置与兼容接口 | Provider 提取与校验 |

## 非目标（当前）

- 自动切换旧 Agent  
- 完整 Compatibility Gateway 实现  
- 双向同步  
- 自动退役旧库  

详见 [`MEMORY_COMPATIBILITY_ARCHITECTURE.md`](./MEMORY_COMPATIBILITY_ARCHITECTURE.md)。

## M-E 验收（设计）

- [x] 权威来源阶段与门禁明确  
- [x] Bridge 先于 Adopted  
- [x] 切换可审计、可回退（设计）  
- [x] 与暂缓清单一致（无自动切换 / 无双向同步）  
