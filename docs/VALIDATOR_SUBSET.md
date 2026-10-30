# Foundation Validator Subset（冻结）

实现：`service/src/mnemosyne/interop/schemas.py` → `validate_against`。

> P3.1：**固定已支持子集**；完整 jsonschema / 生产语义校验仍为 Acceptance 表中的 **Partial（生产化门槛）**，本阶段不扩张。

## 已支持

| 关键字 | 行为 |
| --- | --- |
| `type` | object / array / string / integer / number / boolean / null（含联合类型列表） |
| `required` | 缺字段报错 |
| `properties` | 递归校验已出现字段 |
| `additionalProperties: false` | 拒绝未声明属性 |
| `enum` | 值必须在枚举内 |
| `const` | 值必须相等 |
| `items`（单 schema） | 数组逐项校验 |
| `pattern`（string） | `re.search` |
| component_id 额外 pattern | `^[a-z0-9][a-z0-9._-]*$`（Contract 专用） |

## 明确不支持（不得依赖）

- `minLength` / `maxLength` / `minimum` / `maximum` / `format`
- `$ref` / `$defs` / `allOf` / `anyOf` / `oneOf` / `not`
- `additionalProperties` 为 schema 对象
- `unevaluated*` / `dependentSchemas` / `if-then-else`
- Draft 方言完整合规

未知关键字：**静默忽略**（不报错、不执行）。

## 兼容性测试期望

- 符合支持子集的合法文档 → `ok: true`
- 缺 required / 错 type / 多余属性 / 错 enum·const → `ok: false`
- 仅依赖不支持关键字的约束 → **本阶段不保证拒绝**（已知限制）
