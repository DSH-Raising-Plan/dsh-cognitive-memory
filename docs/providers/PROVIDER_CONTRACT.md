# Provider Contract（草案）

> **轨 B / Workstream 3** · 分支建议：`research/provider-adapters`  
> Adapter **正式实现**须等 [`MEMORY_INTERCHANGE_MODEL.md`](../architecture/MEMORY_INTERCHANGE_MODEL.md) 稳定。

## 数据流（统一）

```
Provider
  → Provider Adapter
  → Memory Interchange Model（Universal Memory Exchange）
  → Migration Engine
  → Mnemosyne Service Contract
  → Observation / Evidence（+ Provenance / Audit）
```

## Adapter 必须实现的能力

| 能力 | 说明 |
| --- | --- |
| `describe()` | Provider 类型、版本、能力声明 |
| `discover(location)` | 校验用户给定路径/凭证；**禁止**未授权全盘扫描 |
| `extract(cursor)` | 分页/游标读取 |
| `to_interchange(batch)` | 映射为 MIM Bundle 片段 |
| `capabilities` | 是否支持 relations、时间精度、删除墓碑等 |

## 映射强制要求

- 外部 ID → `external_id`  
- 来源 → `provenance`（不可丢）  
- 事件时间 vs 记录时间可区分  
- 未知字段进 `extensions` / `payload`，不得静默丢弃关键原文  
- 不发明与 MIM 冲突的平行字段名（研究阶段可用笔记，定稿前收敛）

## 安全

- 凭证不写入 interchange 明文包（引用密钥名即可）  
- 不自动晋升 Active  
- 遵循 Foundation 治理边界：Observation / Evidence / Provenance / Audit  

## 首批目标 Provider

见 [`PROVIDER_MATRIX.md`](./PROVIDER_MATRIX.md)。
