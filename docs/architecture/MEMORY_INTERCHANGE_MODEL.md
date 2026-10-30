# Memory Interchange Model（草案）

> **轨 B / Workstream 1** · 分支建议：`design/memory-interchange`  
> **地位：** 记忆**交换**模型；**不是** Component Contract，也**不是** Mnemosyne 内部 Cognitive Model。  
> **版本目标：** `memory-interchange/0.1-draft`（稳定前可改；稳定后遵循显式版本化）

## 与其它模型的边界

| 模型 | 回答的问题 | 本文件？ |
| --- | --- | --- |
| Component Contract | 组件如何接入 Node | 否（Foundation） |
| **Memory Interchange Model** | 记忆包如何在系统间无损表达与搬运 | **是** |
| Mnemosyne Cognitive Model | Observation / Evidence / Active 等如何治理 | 否（既有服务语义） |

禁止把 P3 UDM 扩成「万能记忆 Schema」。UDM 可作为信封参考，交换载荷用本模型。

## 设计目标

- Provider 无关的规范交换格式  
- 保留 provenance、外部 ID、关系、时间语义  
- 可映射到 Mnemosyne Service Contract（Observation/Evidence），**不**直写核心表  
- Schema 可版本化；未知字段可保留于 extensions

## 规范草案（待定稿字段）

### Envelope

| 字段 | 说明 |
| --- | --- |
| `mim_version` | 交换模型版本，如 `0.1-draft` |
| `bundle_id` | 一次导出/迁移包 ID |
| `exported_at` | 导出时间（UTC） |
| `source` | `{ provider, instance, export_tool }` |
| `items` | `MemoryItem[]` |
| `relations` | `RelationItem[]`（可选） |
| `extensions` | 命名空间扩展 |

### MemoryItem（核心）

| 字段 | 说明 |
| --- | --- |
| `external_id` | 源系统稳定 ID |
| `content` | 主文本 / 结构化摘要 |
| `kind` | 粗分类：`note` / `message` / `fact` / `episode` / `other` |
| `event_time` / `recorded_at` | 事件时间 vs 记录时间（必须可区分） |
| `provenance` | 来源、可信提示、原始指针 |
| `identity_keys` | 可选：用户/会话/线程等映射键 |
| `payload` | 原始或半结构化载荷（opaque 允许） |
| `tags` / `metadata` | 非权威辅助信息 |

### RelationItem

| 字段 | 说明 |
| --- | --- |
| `from_external_id` / `to_external_id` | 端点 |
| `relation` | 类型字符串（映射表由 Provider 提供） |
| `provenance` | 可选 |

### Identity Mapping

迁移时产生 `external_id → mnemosyne_id` 对照表，写入审计与 provenance，支持幂等重跑。

## Schema 落点（草案）

- `schemas/memory-interchange/v0.1-draft.json`（随 design 分支演进）  
- 定稿后升 `v1.json`，写入 `schemas/VERSIONS.json` 的 **独立** 条目（不覆盖 `foundation-0.1.0`）

## 非目标

- 表达完整 Mnemosyne 晋升状态机  
- 替代 PCIP / Component Contract  
- 自动信任任何外部 `kind=fact`
