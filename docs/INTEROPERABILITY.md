# Universal Interoperability Layer

> **P3 Foundation 1.0 — Stabilized**（基线 `foundation-0.1.0` / release `1.0`）。  
> 验收冻结：[`P3_FOUNDATION_ACCEPTANCE.md`](./P3_FOUNDATION_ACCEPTANCE.md)  
> 稳定化：[`P3.1_FOUNDATION_STABILIZATION.md`](./P3.1_FOUNDATION_STABILIZATION.md)  
> 已知限制：[`FOUNDATION_KNOWN_LIMITS.md`](./FOUNDATION_KNOWN_LIMITS.md)  
> 下一站：Production Security Assessment（非自动 P3.2）；保持外部 REST 契约向后兼容。

```
DSH / Agent / App / Plugin / Service
              │
              ▼
    Universal Interoperability
    ├── Component Registry
    ├── Capability Discovery
    ├── Protocol Gateway (REST / MCP / CLI)
    ├── Schema Registry (schemas/)
    ├── SDK / Bindings
    ├── Event Gateway (Outbox)
    ├── Identity / Authorization
    └── Adapter Runtime
              │
              ▼
        Mnemosyne Core (MemoryService)
```

互操作层**不复制** Memory / Evidence / Retrieval 业务逻辑。

## 六项标准（本仓库）

| 标准 | 状态 | 位置 |
| --- | --- | --- |
| Universal Data Model | Foundation Verified（基础 Schema） | `schemas/universal-data-model/` |
| Universal API | Partial | REST `/api/v1` |
| Universal Protocol | Partial | REST + MCP + CLI |
| Component Contract | Foundation Verified（基础校验） | `schemas/component-contract/` |
| Universal Event System | Partial | events + Outbox |
| Universal Governance | Partial（scopes 基础）；生产级身份 Planned/Partial | token + component scopes + Capability Gate |

## 外部实证

- 适配器：`examples/external-weather-adapter/`（REST only，不 import `mnemosyne`）
- 探针：`scripts/run_external_interop_probe.py`（注册 / Discovery / PCIP L1·L3 / Observation 隔离）

## SDK

- Python：`packages/mnemosyne-sdk`（薄封装 REST）
- TypeScript：仓库 `src/memory-client.js` 与 `packages/mnemosyne-sdk-ts`
