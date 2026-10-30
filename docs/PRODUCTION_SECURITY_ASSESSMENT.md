# Production Security Assessment（下一阶段 · 先报告、不开 PR）

> 状态：**Completed**  
> 差距报告：[`reports/PRODUCTION_SECURITY_GAP_REPORT.md`](./reports/PRODUCTION_SECURITY_GAP_REPORT.md)  
> 后续：**Production Hardening = Deferred**；工程进入「稳定基线维护与真实使用反馈」。  
> 加固 PR 仅在 [`ENGINEERING_CONSTRAINTS.md`](./ENGINEERING_CONSTRAINTS.md) 所列触发条件出现时再开。

## 原则

- 不预设必须新增哪些模块（身份、P2P、策略引擎等均待评估后决定）。
- 加固方案必须遵守 [`ENGINEERING_CONSTRAINTS.md`](./ENGINEERING_CONSTRAINTS.md)。
- Foundation Verified 契约保持向后兼容；破坏性项须显式版本化。

## 待评估候选项（来自已知限制，非承诺）

| ID | 议题 | 初判风险维度 | 攻击面 | 修复成本（粗） | 兼容性影响 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| L-02 | `require_component=false` 时 Bearer≈本地全权 | 高（误暴露时） | 持有 token 的本机/进程 | 中 | 低→中（默认收紧需迁移说明） | 本地信任模式 |
| L-03 | 无对等节点密码学身份 | 中（联邦场景） | PCIP 入站伪造 | 高 | 中（新身份层） | 入站已 `untrusted` |
| L-04 | `allow_train` / `allow_forward` 未深层执法 | 中 | 数据出口/二次使用 | 中→高 | 低（加强执法） | Observation 隔离已有 |
| L-01 | Validator 非完整 JSON Schema | 低→中 | 畸形契约绕过校验期望 | 中 | 低（收紧校验可能拒旧客户端） | 见 `VALIDATOR_SUBSET.md` |
| L-05 | 无 P2P / Relay | 视需求 | N/A until 启用 | 高 | 高（新协议面） | **仅当有真实接入需求** |
| L-06/L-07 | SDK 习惯差 / PCIP 错误体形态 | 低 | 客户端解析 | 低 | 低（冻结为已知） | 文档化即可 |

## 建议输出（报告结构）

1. **资产与信任边界**：Node、Bearer、Component、PCIP、外部 REST  
2. **威胁场景**：token 泄露、恶意组件自注册、伪造入站、策略绕过  
3. **差距排序表**：风险 × 攻击面 × 成本 × 兼容性  
4. **推荐批次**：P0 必做 / P1 可排期 / 明确不做（暂无需求）  
5. **兼容策略**：每项加固如何保持或版本化 Foundation 契约  

## 退出条件

- 有一份可评审的评估报告（可放 `docs/reports/`）  
- 明确下一轮生产加固范围（或明确“暂缓加固、维持 Foundation”）  
- **仍不自动开 P3.2**，除非评估结论驱动立项
