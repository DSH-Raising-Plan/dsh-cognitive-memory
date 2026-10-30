# Universal Interoperability Layer

> 成熟度：**Foundation Verified**（PR [#17](https://github.com/DSH-Raising-Plan/dsh-mnemosyne/pull/17)）；完整生产化与 P2P/Relay 仍为 Partial / Planned。  
> 验收表：[`P3_FOUNDATION_ACCEPTANCE.md`](./P3_FOUNDATION_ACCEPTANCE.md)

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
