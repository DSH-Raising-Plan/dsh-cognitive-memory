# P3 Universal Ecosystem — Foundation 验收状态

> PR：[#17](https://github.com/DSH-Raising-Plan/dsh-mnemosyne/pull/17)  
> 分支：`feat/mnemosyne-2.0-p3-ecosystem`  
> 验收结论：**Foundation Accepted（不阻塞合并）**  
> 证据：外部 REST 组件 `examples/external-weather-adapter`（不 import `mnemosyne`）经 `scripts/run_external_interop_probe.py` **12/12 PASS**

## 状态约定

| 标签 | 含义 |
| --- | --- |
| **Foundation Verified** | 本阶段互操作基础已用外部组件实证；可作为 #17 Foundation 验收通过依据 |
| **Partial** | 有实现但未达生产语义/完整强度；**不阻塞** Foundation，列为生产化门槛 |
| **Planned** | 明确未交付；**不阻塞** Foundation，列为后续联邦/生产化门槛 |

## 能力验收表

| 能力 | 状态 | 证据 / 门槛说明 |
| --- | --- | --- |
| Universal Data Model 基础 Schema | **Foundation Verified** | `schemas/universal-data-model/v1.json` + `/udm/validate`；探针 `contract.validate` 同源链路 |
| Component Contract 基础校验 | **Foundation Verified** | `schemas/component-contract/v1.json`；注册前校验；探针 `contract.validate` / `component.register` |
| 外部 REST 注册与 Discovery | **Foundation Verified** | 外部适配器 token→register→`GET /discovery`；`pcip.l3_default=forbidden` |
| PCIP L1/L3 基础安全边界 | **Foundation Verified** | L3 → 403；过期策略 / `to_node` 错配拒绝；route scopes |
| L3 默认拒绝、Observation 隔离 | **Foundation Verified** | 入站仅 Observation、`trust=untrusted`；无自动 Active semantic |
| 完整 Schema 语义校验 | **Partial** | 轻量子集校验器；缺 minLength/format/完整 jsonschema → **生产化门槛** |
| 生产级组件身份与授权 | **Partial** | Bearer + scopes + bootstrap register；缺密码学组件身份 / 强制 `require_component` → **生产化门槛** |
| 数据使用策略深层执法 | **Planned** | `allow_train` / `allow_forward` 等未深层执法 → **生产化门槛** |
| P2P / Relay Federation | **Planned** | 仅 local API stub → **联邦门槛** |

## 里程碑意义

阶段 4 已不只是内部定义互操作标准：存在一个**不依赖 Mnemosyne 内部实现**的外部组件，真实走通了

**注册 → 发现 → 授权（scopes）→ 交换（PCIP L1）→ 安全拒绝（L3 / 过期 / 错节点）**。

剩余 Partial / Planned **不得**用来否定 Foundation 验收；合入后应作为生产化与联邦路线的明确门槛跟踪。

## 复验命令

```bash
PYTHONPATH=service/src python -m unittest discover -s service/tests/unit
python scripts/run_external_interop_probe.py
```
