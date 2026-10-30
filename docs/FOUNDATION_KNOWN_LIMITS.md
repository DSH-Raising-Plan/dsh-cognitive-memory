# Foundation 已知限制清单（稳定基线）

与 [`P3_FOUNDATION_ACCEPTANCE.md`](./P3_FOUNDATION_ACCEPTANCE.md) 中 Partial / Planned 对齐；**不是** Foundation 否决项。

| ID | 限制 | 状态 | 备注 |
| --- | --- | --- | --- |
| L-01 | Validator 非完整 JSON Schema | Partial | 见 `VALIDATOR_SUBSET.md` |
| L-02 | `require_component=false` 时 Bearer≈本地全权 | Partial | 生产安全差距评估后再决策 |
| L-03 | 无对等节点密码学身份 | Partial / Planned | PCIP 入站 `trust=untrusted` |
| L-04 | `allow_train` / `allow_forward` 未深层执法 | Planned | 仅 Observation 落地隔离 |
| L-05 | 无 P2P / Relay 传输 | Planned | Discovery 标明 `local_api_only` |
| L-06 | SDK `observe`/`search` 入参形态略有语言习惯差 | Mitigated in P3.1 | 核心 HTTP 路径已对齐；见 SDK 一致性测试 |
| L-07 | PCIP 失败体在 HTTP detail 内嵌 `ok/detail` | Frozen | 客户端应读 status + detail |

生成稳定性报告时会附带本清单。
