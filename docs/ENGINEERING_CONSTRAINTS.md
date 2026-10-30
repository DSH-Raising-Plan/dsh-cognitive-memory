# Mnemosyne 后续开发约束（冻结）

> 生效自：**P3 Foundation 1.0 — Stabilized**（#18）  
> 工程分界：**Foundation 负责稳定；后续演进负责增强。两者不得混为一谈。**

## 四条硬约束

1. **向后兼容优先**  
   已验证的外部 REST 契约（见 [`P3_FOUNDATION_ACCEPTANCE.md`](./P3_FOUNDATION_ACCEPTANCE.md) Foundation Verified 项）不得被无意破坏。改动须能被外部探针 / Foundation CI 复验。

2. **安全能力渐进增强**  
   可以增加身份验证、授权和策略执行能力；**不得削弱**既有安全边界（L3 默认拒绝、Observation 隔离、过期/`to_node`/scope 拒绝等）。

3. **破坏性变更显式版本化**  
   任何破坏兼容的变更必须同时具备：版本升级、兼容策略、迁移路径。禁止用“顺手重构”静默改契约。

4. **不为路线图而开发**  
   **不自动开启 P3.2。** 先做 [Production Security Assessment](./PRODUCTION_SECURITY_ASSESSMENT.md)，再根据实际风险与接入需求决定投入。

## 与 Foundation 的关系

| 层 | 职责 |
| --- | --- |
| Foundation（已稳定） | 可维护、可复现的互操作基线；契约冻结 |
| 后续演进 | 在兼容策略下增强生产安全与能力；经评估再立项 |

## 检查清单（每个后续 PR）

- [ ] 是否触及 Foundation Verified 表面？若是，外部探针 / `foundation-stabilization` 是否仍绿？
- [ ] 是否收紧或削弱既有拒绝路径？削弱则否决。
- [ ] 若破坏兼容：版本 / 兼容矩阵 / 迁移说明是否齐全？
- [ ] 是否仅为“路线图下一站”而无真实风险/接入驱动？若是，暂缓。
