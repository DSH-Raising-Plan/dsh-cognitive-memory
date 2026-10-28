# dsh-cognitive-memory

DeepSeek Harness **认知记忆**插件：拉起外置 [cognitive-memory](../../services/cognitive-memory) 子进程，用 REST 暴露检索 / 上下文 / 观察 / 反馈工具。

**替代**旧 A-MEM（Chroma 进程内向量库）方案。

## 安装

需本机 Python ≥ 3.11，并安装服务依赖：

```bash
pip install -e ../../services/cognitive-memory
dsh plugin --profile web add github:DSH-Raising-Plan/dsh-cognitive-memory#plugin/dsh
```

本地开发可将插件路径指到本目录；服务根目录默认识别 monorepo 的 `services/cognitive-memory`。

## 工具

| 工具 | 作用 |
| --- | --- |
| `memory_health` | 健康检查 |
| `memory_search` | 搜索记忆 |
| `memory_get` | 详情 + 证据 |
| `memory_context` | 组装上下文（快速通道） |
| `memory_propose` | 提交候选记忆 |
| `memory_observe` | 提交原始观察 |
| `memory_feedback` | 有用/有误反馈 |
| `memory_update` / `memory_forget` | 更新 / 失效 |
| `memory_task_status` | 后台任务 |

## 配置（cordis）

```yaml
dsh-cognitive-memory:
  auto_start: true
  # service_root: D:/path/to/services/cognitive-memory
  # data_dir: C:/Users/.../AppData/Local/DSH/cognitive-memory
  # token: 可选；不设则自动生成并写入 runtime/token
  # base_url: 若服务已外部启动，可只填 base_url + token
```

## 许可

AGPL-3.0-or-later
