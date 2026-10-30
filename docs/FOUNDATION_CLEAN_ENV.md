# 干净环境复现（P3.1-D）

目标：在新环境按文档接入独立 REST 组件并跑通 Foundation 探针，不依赖本机脏状态。

## 前置

- Python 3.11+（推荐 3.12）
- 网络可访问本机回环

## 步骤

```bash
git clone <repo> && cd dsh-mnemosyne
git checkout feat/mnemosyne-2.0-p3.1-foundation-stabilization   # 或合入后的标签

python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -e ./service
pip install httpx uvicorn fastapi pydantic

# 一键：起临时 Node + 外部天气适配器探针（12 项）
python scripts/run_external_interop_probe.py
```

期望：末行 `passed=12 failed=0 total=12`，进程退出码 `0`。

## 手动拆分（可选）

```bash
export DSH_MEMORY_TOKEN=probe-token
python -m mnemosyne.main --data-dir /tmp/mnemosyne-clean --host 127.0.0.1 --port 8765 --token probe-token
# 另一终端：
python examples/external-weather-adapter/external_weather_adapter.py http://127.0.0.1:8765 probe-token
```

## 验收对照

唯一基准：[`P3_FOUNDATION_ACCEPTANCE.md`](./P3_FOUNDATION_ACCEPTANCE.md)  
版本基线：`schemas/VERSIONS.json` → `foundation-0.1.0`
