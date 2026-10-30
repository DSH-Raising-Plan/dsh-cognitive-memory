# Foundation 兼容性矩阵

基线 ID：`foundation-0.1.0`（见 `schemas/VERSIONS.json`）

| 服务端 (`service`) | Schema baseline | SDK Python | SDK TS | 外部探针 |
| --- | --- | --- | --- | --- |
| `>=0.3.4` | `foundation-0.1.0` | `0.1.x` | `0.1.x` | `examples/external-weather-adapter` |

## 独立版本（勿用 Mnemosyne 整包版本隐式表达）

| 面 | 版本字段 | 当前值 |
| --- | --- | --- |
| REST API | `mnemosyne_api` / Discovery | `v1` |
| UDM | `udm_version` | `1.0` |
| Component Contract | schema path `v1` | `1.0` |
| Events | schema path `v1` | `1.0` |
| PCIP | `pcip_version` | `0.1-proposal` |
| SDK Python | `packages/mnemosyne-sdk` | `0.1.0` |
| SDK TS | `packages/mnemosyne-sdk-ts` | `0.1.0` |

## 不兼容信号（应失败或明确拒绝）

- `pcip_version` ≠ `0.1-proposal`
- `udm_version` ≠ `1.0`
- Contract 缺 required / `additionalProperties` 违规
- 组件缺所需 scope 访问 Discovery / PCIP
