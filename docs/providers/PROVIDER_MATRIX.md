# Provider Matrix（首批）

> 验证「架构能否接入外部记忆」；**至少两种不同类型**源走通同一管线。

| Provider | 类型 | 验证目标 | 批次 | 状态 |
| --- | --- | --- | --- | --- |
| JSON / JSONL | 结构化交换 | 通用交换格式 | 1 | 研究中 |
| Markdown | 非结构化文本 | 个人笔记/知识文档 | 1 | 研究中 |
| SQLite | 本地结构化 | 表、关系、本地文件 | 1 | 研究中 |
| Mem0 | 外部 Memory API | 用户标识与操作语义 | 1 | 研究中 |
| Zep / Graphiti | 图/会话记忆 | API + 图关系 | 2 | 暂缓 |
| Letta | Agent 记忆运行时 | 兼容语义 | 2 | 暂缓 |

## 覆盖维度

| 维度 | 覆盖来源 |
| --- | --- |
| 结构化记录 | JSON、SQLite |
| 自由文本 | Markdown |
| 关系/表 | SQLite（+ 日后 Graphiti） |
| 远程 API / 用户键 | Mem0 |

## 成功标准（M-C）

- ≥2 个不同类型 Provider：样本 → MIM 映射文档 + 样例 Bundle  
- 字段对照表见 [`PROVIDER_MAPPING_GUIDE.md`](./PROVIDER_MAPPING_GUIDE.md)  
- **不**要求此时已写入 Mnemosyne 生产库  

## 样本落点（建议）

`research/provider-adapters` 分支：`samples/providers/{json,markdown,sqlite,mem0}/`
