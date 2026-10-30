# Universal Interoperability Layer

> 成熟度：**Partial**（契约 + 本地注册/发现 + PCIP stub）；P2P/Relay **Planned**。

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
| Universal Data Model | Implemented (schema) | `schemas/universal-data-model/` |
| Universal API | Partial | REST `/api/v1` |
| Universal Protocol | Partial | REST + MCP + CLI |
| Component Contract | Implemented (schema+validate) | `schemas/component-contract/` |
| Universal Event System | Partial | events + Outbox |
| Universal Governance | Partial | token + component scopes + Capability Gate |

## SDK

- Python：`packages/mnemosyne-sdk`（薄封装 REST）
- TypeScript：仓库 `src/memory-client.js` 与 `packages/mnemosyne-sdk-ts`
