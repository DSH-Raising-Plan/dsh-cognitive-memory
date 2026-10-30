# Provider Matrix（首批）

> **M-C Accepted（映射验证）** — 四类源均已手工映射到 MIM `0.1`；≥2 种不同类型满足退出条件。

| Provider | 类型 | 验证目标 | 批次 | 状态 |
| --- | --- | --- | --- | --- |
| JSON / JSONL | 结构化交换 | 通用交换格式 | 1 | **Mapped** → `samples/providers/json/` |
| Markdown | 非结构化文本 | 个人笔记/知识文档 | 1 | **Mapped** → `samples/providers/markdown/` |
| SQLite | 本地结构化 | 表、关系、本地文件 | 1 | **Mapped** → `samples/providers/sqlite/` |
| Mem0 | 外部 Memory API | 用户标识与操作语义 | 1 | **Mapped** → `samples/providers/mem0/` |
| Zep / Graphiti | 图/会话记忆 | API + 图关系 | 2 | 暂缓 |
| Letta | Agent 记忆运行时 | 兼容语义 | 2 | 暂缓 |

## 覆盖维度

| 维度 | 覆盖来源 |
| --- | --- |
| 结构化记录 | JSON、SQLite |
| 自由文本 | Markdown |
| 关系/表 | SQLite |
| 远程 API / 用户键 | Mem0 |

## 成功标准（M-C）

- [x] ≥2 个不同类型 Provider：样本 → MIM 映射  
- [x] 字段对照见 [`PROVIDER_MAPPING_GUIDE.md`](./PROVIDER_MAPPING_GUIDE.md)  
- [x] `python scripts/validate_mim_samples.py` 全绿  
- [x] **未**写入 Mnemosyne 生产库（仅交换层验证）  
