# Provider Mapping Guide（草案）

> 各 Provider → Memory Interchange Model 的字段对照。研究阶段允许笔记；**定稿前收敛到 MIM**。

## 通用规则

1. 每个源记录必须有稳定 `external_id`（无则确定性哈希，写入 provenance）  
2. `content` 为人类可读主载荷；完整原文可放 `payload`  
3. `provenance.provider` = 矩阵中的 Provider 名  
4. 关系单独进 `relations[]`，勿把图硬塞进单条 `metadata`  
5. 删除/墓碑：首批可仅文档化；执行层策略在 Migration Plan 中显式声明  

---

## JSON / JSONL

| 源 | MIM |
| --- | --- |
| 对象 `id` / `_id` | `external_id` |
| `text` / `content` / `body` | `content` |
| `created_at` / `timestamp` | `recorded_at` 或 `event_time`（按语义标注） |
| 其余键 | `payload` 或 `metadata` |
| 文件路径 / 行号 | `provenance.raw_ref` |

样例期望：`samples/providers/json/`

---

## Markdown

| 源 | MIM |
| --- | --- |
| 文件路径 + 标题锚点 / 块 hash | `external_id` |
| 正文 | `content` |
| front matter 日期 | `event_time` / `recorded_at` |
| front matter 标签 | `tags` |
| 整文件 | `payload`（可选） |
| `kind` | 默认 `note` |

---

## SQLite

| 源 | MIM |
| --- | --- |
| `table` + PK | `external_id`（如 `memories:42`） |
| 文本列 | `content` |
| 时间列 | 显式映射表（每库一份） |
| FK / link 表 | `relations[]` |
| DB 文件路径 | `provenance.raw_ref` |

每库需一份 **table→field** 映射声明，禁止隐式猜列。

---

## Mem0

| 源 | MIM |
| --- | --- |
| memory id | `external_id` |
| memory text | `content` |
| user / agent / run id | `identity_keys` |
| created/updated | 时间字段 |
| metadata | `metadata` / `payload` |
| API 端点 / org | `provenance` |

注意：API 语义（add/search/update/delete）属 Compatibility 评估，**首批只做导出/拉取映射**。

---

## 验证检查表（每个 Provider）

| Provider | 样例 | 时间语义 | MIM 0.1 | provenance | 无冲突私有必填 |
| --- | --- | --- | --- | --- | --- |
| JSON | ✓ | ✓ | ✓ | ✓ | ✓ |
| Markdown | ✓ | ✓ | ✓ | ✓ | ✓ |
| SQLite | ✓ + table_map | ✓ | ✓ + relations | ✓ | ✓ |
| Mem0 | ✓ fixture | ✓ | ✓ + identity_keys | ✓ | ✓ |

统一校验：`python scripts/validate_mim_samples.py`  
