# Provider mapping samples（轨 B / Workstream 3 · M-C）

四类源均已产出符合 MIM `0.1` 的 `mapped.mim.json`。校验：

```bash
python scripts/build_sqlite_sample.py   # 如需重建 sqlite 文件
python scripts/validate_mim_samples.py
```

| 目录 | Provider | 类型 | 状态 |
| --- | --- | --- | --- |
| `json/` | JSON / JSONL | 结构化 | 已映射 |
| `markdown/` | Markdown | 非结构化文本 | 已映射 |
| `sqlite/` | SQLite | 本地结构化 + 关系 | 已映射（含 `table_map.json`） |
| `mem0/` | Mem0 | 外部 API fixture | 已映射（无真实密钥） |

正式 Adapter 实现须等进入 `2.1` 实现轨。详见 `docs/providers/`。
