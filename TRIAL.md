# 试用立场：值得用，还不值得只信它

> 成熟度：**Partial**（可并行试用；未达主记忆 / Safe Upgrade Candidate）  
> 路线：[docs/MNEMOSYNE_2.0_FINAL_PLAN.md](./docs/MNEMOSYNE_2.0_FINAL_PLAN.md)

本插件 / 服务当前定位是 **副记忆（并行观察）**，不是「唯一记忆」。

## 推荐用法

1. 独立 `data_dir`（与默认目录分开亦可），**每天备份 SQLite**。
2. 与现有 A-MEM / hybrid 等 **并行 1–2 周**：`enable=true`，`replace_a_mem=false`。
3. 只观察三件事：召回准不准、启动/调用稳不稳、服务挂了对话能否继续。
4. 一旦出现「记错且无法回滚」，立刻关掉 `enable` 或保持副记忆位。

## 每天备份

```bash
# 在仓库或已安装的 service/ 下
pip install -e ./service   # 首次
python -m mnemosyne.cli backup --data-dir "%LOCALAPPDATA%/DSH/mnemosyne"
# 或使用脚本（Windows）：
# scripts/backup-daily.ps1
```

恢复：

```bash
python -m mnemosyne.cli restore <backup.db> --data-dir "..." --force
```

从旧 A-MEM 导入（候选，不直接当 ACTIVE）：

```bash
python -m mnemosyne.cli migrate-amem --jsonl path/to/export.jsonl
```

## 什么时候可以当主记忆

| 门槛 | 成熟度 | 说明 |
| --- | --- | --- |
| `dsh plugin add` 后零配置能起 | Planned | 仓库含 `service/`；装进 profile 后**尚未现场验收** |
| 真实对话：`observe` → 下一轮自动 `context` | Planned | Host mock 测 ≠ 真 DSH E2E |
| 备份 / 导出 / 迁移 | Partial | CLI 有；完整 round-trip + 升级前备份见 P0 |
| 进程锁 + 删除级联（Safe Upgrade） | Partial | P0 Safety Hardening |
| 最小 CI（插件 + 服务 + 端到端） | Partial | 单元/契约有；对话闭环未进 CI |
| 连续一周无丢 / 串记忆 | Planned | 未跑 |
| 正式 MCP 标准客户端 | Planned | 当前自研 JSON-RPC 桩 |

**一句话：** 现在值得用、值得每天用；证明不会把经历弄丢或弄错之前，先当副记忆。
