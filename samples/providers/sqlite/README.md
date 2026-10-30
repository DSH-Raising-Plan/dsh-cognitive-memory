# SQLite provider sample

- `sample.sqlite` — 由 `python scripts/build_sqlite_sample.py` 生成  
- `table_map.json` — 显式 table→field 映射（禁止隐式猜列）  
- `mapped.mim.json` — MIM `0.1` Bundle（含 `relations`）

用户须明确指定 DB 路径；禁止自动全盘扫描。
