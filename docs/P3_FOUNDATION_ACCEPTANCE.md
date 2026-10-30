# P3 Universal Ecosystem — Foundation 验收状态

> PR：[#17](https://github.com/DSH-Raising-Plan/dsh-mnemosyne/pull/17)  
> 分支：`feat/mnemosyne-2.0-p3-ecosystem`  
> 验收结论：**Foundation Accepted（不阻塞合并）**  
> **P3.1 冻结：** 本文件为唯一验收基准；稳定化见 [`P3.1_FOUNDATION_STABILIZATION.md`](./P3.1_FOUNDATION_STABILIZATION.md)  
> 版本基线：`schemas/VERSIONS.json` → **`foundation-0.1.0`**  
> 证据：外部 REST 组件 `examples/external-weather-adapter`（不 import `mnemosyne`）经 `scripts/run_external_interop_probe.py` **12/12 PASS**

## 状态约定

| 标签 | 含义 |
| --- | --- |
| **Foundation Verified** | 本阶段互操作基础已用外部组件实证；可作为 #17 Foundation 验收通过依据 |
| **Partial** | 有实现但未达生产语义/完整强度；**不阻塞** Foundation，列为生产化门槛 |
| **Planned** | 明确未交付；**不阻塞** Foundation，列为后续联邦/生产化门槛 |

## 能力验收表（冻结 — 不得在 P3.1 扩张）

| 能力 | 状态 | 证据 / 门槛说明 |
| --- | --- | --- |
| Universal Data Model 基础 Schema | **Foundation Verified** | `schemas/universal-data-model/v1.json` + `/udm/validate` |
| Component Contract 基础校验 | **Foundation Verified** | `schemas/component-contract/v1.json`；注册前校验 |
| 外部 REST 注册与 Discovery | **Foundation Verified** | token→register→`GET /discovery`；`pcip.l3_default=forbidden` |
| PCIP 基础交换流程 | **Foundation Verified** | L1 accept → Observation |
| PCIP L1/L3 基础安全边界 | **Foundation Verified** | L3 → 403；过期 / `to_node` 错配；route scopes |
| L3 默认拒绝 | **Foundation Verified** | 默认禁止私人记忆交换 |
| L1 内容进入 Observation | **Foundation Verified** | `accepted_as_observation`；`trust=untrusted` |
| 外部内容不自动晋升 Active Memory | **Foundation Verified** | 探针 `no_auto_active_semantic` |
| 过期、错误目标节点、权限边界拒绝 | **Foundation Verified** | `policy_expired` / `to_node_mismatch` / insufficient scope |
| 完整 Schema 语义校验 | **Partial** | 见 `VALIDATOR_SUBSET.md` → **生产化门槛** |
| 生产级组件身份与授权 | **Partial** | → **生产化门槛**（P3.1 后评估） |
| 数据使用策略深层执法 | **Planned** | → **生产化门槛** |
| P2P / Relay Federation | **Planned** | → **联邦门槛** |

## 里程碑意义

阶段 4 已不只是内部定义互操作标准：存在一个**不依赖 Mnemosyne 内部实现**的外部组件，真实走通了

**注册 → 发现 → 授权（scopes）→ 交换（PCIP L1）→ 安全拒绝（L3 / 过期 / 错节点）**。

剩余 Partial / Planned **不得**用来否定 Foundation 验收；也**不得**在 P3.1 稳定化中偷偷变成承诺。

## 复验命令

```bash
PYTHONPATH=service/src python -m unittest discover -s service/tests/unit
python scripts/run_external_interop_probe.py
python scripts/generate_foundation_stability_report.py
```
