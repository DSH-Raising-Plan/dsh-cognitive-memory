# Memory Interchange Model

> **轨 B / Workstream 1 · M-A Accepted（设计冻结）**  
> **版本：** `memory-interchange/0.1`  
> **地位：** 记忆**交换**模型；**不是** Component Contract，也**不是** Mnemosyne 内部 Cognitive Model。  
> **Schema：** [`schemas/memory-interchange/v0.1.json`](../../schemas/memory-interchange/v0.1.json)

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
- Schema 可版本化；未知字段可保留于 `extensions` / `payload`

## 规范（0.1 冻结）

### Envelope

| 字段 | 说明 |
| --- | --- |
| `mim_version` | 固定 `0.1` |
| `bundle_id` | 一次导出/迁移包 ID |
| `exported_at` | 导出时间（UTC，ISO-8601） |
| `source` | `{ provider, instance?, export_tool? }` |
| `items` | `MemoryItem[]` |
| `relations` | `RelationItem[]`（可选） |
| `extensions` | 命名空间扩展（可选） |

### MemoryItem

| 字段 | 说明 |
| --- | --- |
| `external_id` | 源系统稳定 ID（必填） |
| `content` | 主文本 / 结构化摘要（必填） |
| `kind` | `note` / `message` / `fact` / `episode` / `other` |
| `event_time` / `recorded_at` | 事件时间 vs 记录时间（语义必须可区分） |
| `provenance` | 来源、可信提示、原始指针（必填） |
| `identity_keys` | 可选：用户/会话/线程等映射键 |
| `payload` | 原始或半结构化载荷（opaque 允许） |
| `tags` / `metadata` | 非权威辅助信息 |

### RelationItem

| 字段 | 说明 |
| --- | --- |
| `from_external_id` / `to_external_id` | 端点 |
| `relation` | 类型字符串（映射表由 Provider 提供） |
| `provenance` | 可选 |

### Provenance

| 字段 | 说明 |
| --- | --- |
| `provider` | Provider 名（必填） |
| `raw_ref` | 原始指针（路径/行号/API id） |
| `trust_hint` | `untrusted` / `user_asserted` / `verified` |
| `notes` | 自由说明 |

### Identity Mapping（迁移侧产物，不在 Bundle 内强制）

迁移执行产生 `external_id → mnemosyne_id` 对照表，写入审计与 provenance，支持幂等重跑。对照表 schema 见迁移架构文档。

## Import / Export Contract

| 方向 | 约定 |
| --- | --- |
| **Export** | 任意 Mnemosyne 可读投影 → MIM Bundle（`mim_version` + provenance） |
| **Import** | 外部源 → Adapter → MIM Bundle → Migration Engine（不得跳过 MIM） |
| **往返** | Export 后再 Import 不得要求破坏性字段；`payload`/`extensions` 允许保留未知键 |
| **权威** | MIM **不**声明 Active/权威；权威切换属 Adoption |

## 版本与兼容策略

| 规则 | 说明 |
| --- | --- |
| 当前冻结 | `0.1` |
| 兼容加字段 | 次版本（如 `0.2`）：仅 additive；旧消费者忽略未知 `extensions` |
| 破坏变更 | 主版本（如 `1.0`）：须迁移说明 + 双读窗口 |
| 与 Foundation | **独立**版本线；**不**写入 `foundation-0.1.0` 契约面 |
| 校验 | `scripts/validate_mim_samples.py` 校验 `samples/providers/**/mapped.mim.json` |

## 非目标

- 表达完整 Mnemosyne 晋升状态机  
- 替代 PCIP / Component Contract  
- 自动信任任何外部 `kind=fact`
