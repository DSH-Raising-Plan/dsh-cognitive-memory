# Universal Component Contract

> 成熟度：**Implemented**（Schema + 注册校验）；运行时权限见 P2 `component_auth`。  
> Schema：[`schemas/component-contract/v1.json`](../schemas/component-contract/v1.json)

## 组件类型

| 类型 | 作用 | 示例 |
| --- | --- | --- |
| Provider | 提供外部能力 | Embedding、Reranker |
| Consumer | 调用 Mnemosyne | Agent、App |
| Adapter | 协议/数据转换 | DSH |
| Extension | 扩展内部能力 | 自定义 Retrieval |
| Storage | 存储后端（特殊契约） | SQLite（默认） |

Storage Provider 需要事务 / 备份 / 迁移契约，**不能**当作普通插件任意替换。

## 原则

1. 注册 ≠ 授权。
2. 外部组件不直接写核心数据库。
3. 兼容性声明（`mnemosyne_api`）必须可检查。
4. 协议：`rest` / `mcp` / `cli` / `stdio` / `webhook` / `pcip`。
