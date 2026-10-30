# Mnemosyne 后续开发约束（冻结）

> 生效自：**P3 Foundation 1.0 — Stabilized**（#18）  
> 工程分界：**Foundation 负责稳定；后续演进负责增强。两者不得混为一谈。**  
> 当前工程阶段：**双轨并行** — 轨 A 稳定基线维护；轨 B Migration & Adoption **设计已 Accepted**（实现 Deferred；见 [`plans/MEMORY_MIGRATION_PARALLEL_PLAN.md`](./plans/MEMORY_MIGRATION_PARALLEL_PLAN.md)）

## 三条安全原则（持续约束后续实现）

1. **不因支持更多部署方式而默认放宽安全边界。**  
   新增部署形态（远程访问、托管、多客户端等）必须显式收紧或保持边界，不得为了「能跑起来」而降低默认拒绝/隔离强度。

2. **不因数据携带 `allow_train` / `allow_forward` 字段，就宣称已经执行相应策略。**  
   Schema 声明 ≠ 执法。在统一出口门闩落地并有测试证据之前，产品与文档不得声称已执行训练/转发限制。

3. **不因两个节点能够通信，就默认它们彼此可信。**  
   可达性 ≠ 身份可信。跨节点内容默认不可信，直至存在可验证的身份与授权机制。

## 四条工程硬约束

1. **向后兼容优先**  
   已验证的外部 REST 契约（见 [`P3_FOUNDATION_ACCEPTANCE.md`](./P3_FOUNDATION_ACCEPTANCE.md) Foundation Verified 项）不得被无意破坏。改动须能被外部探针 / Foundation CI 复验。

2. **安全能力渐进增强**  
   可以增加身份验证、授权和策略执行能力；**不得削弱**既有安全边界（L3 默认拒绝、Observation 隔离、过期/`to_node`/scope 拒绝等）。与上方三条安全原则一并执行。

3. **破坏性变更显式版本化**  
   任何破坏兼容的变更必须同时具备：版本升级、兼容策略、迁移路径。禁止用“顺手重构”静默改契约。

4. **不为路线图而开发**  
   **不自动开启 P3.2。** Production Security Assessment 已完成；**Production Hardening 默认 Deferred**，仅在触发条件出现时重新打开决策。轨 B 设计**不**等于批准进入 `2.1` 实现轨。

## Memory Migration & Adoption（轨 B 硬约束）

1. **不得直接改变** Foundation 1.0 现有 REST Contract、PCIP Contract、Component Contract。  
2. 若确需扩展公共面：须兼容性评估 + **显式版本升级**；禁止静默改契约。  
3. 外源记忆默认经 **Observation / Evidence**；**不**自动 Active；**不**直写核心库。  
4. 保留 **Provenance / Audit**；批次可预览、可验证、可回滚。  
5. **暂缓：** 双向同步、自动切换 Agent、完整 Compatibility Gateway、未授权全盘扫描、自动退役旧库、P2P/Relay。  
6. Memory Interchange Model、Component Contract、Cognitive Model **三分**，禁止混成单一万能 Schema。  
7. Provider **研究**可并行；Adapter **正式实现**须等 Interchange Contract 稳定。

## 与 Foundation 的关系

| 层 | 职责 |
| --- | --- |
| Foundation（已稳定） | 可维护、可复现的互操作基线；契约冻结 |
| 轨 A 维护（当前） | 修阻塞复现/兼容的缺陷；CI / 安全边界不退化；不扩生态能力 |
| 轨 B 设计（已 Accepted） | MIM 0.1 + 迁移/Adoption 设计 + 四类 Provider 映射；`2.1` 实现须另开决策 |
| 后续演进 | 仅在触发条件 + 评估结论（含轨 B 退出条件）驱动下增强 |

## 何时重新打开「生产安全加固」决策

仅当出现以下**真实需求**之一：

- 用户需要**远程访问**自己的 Mnemosyne Node  
- 开始接入**不可信第三方组件**  
- 开始建立**跨节点信任关系**  
- 需要**对外承诺**训练或转发限制  
- 准备开放 **P2P / Relay**

否则保持 Hardening **Deferred**，继续基线维护。

## 检查清单（每个后续 PR）

- [ ] 是否触及 Foundation Verified 表面？若是，外部探针 / `foundation-stabilization` 是否仍绿？
- [ ] 是否收紧或削弱既有拒绝路径？削弱则否决。
- [ ] 是否违反三条安全原则（部署放宽 / 假称策略执法 / 通信即信任）？
- [ ] 若破坏兼容：版本 / 兼容矩阵 / 迁移说明是否齐全？
- [ ] 是否仅为“路线图下一站”或无触发条件的加固？若是，暂缓。
- [ ] 若属轨 B：是否改动了 Foundation REST/PCIP/Component？若是且无版本升级评估，否决。
- [ ] 若属轨 B 实现：是否仍落在暂缓清单（双向同步 / 自动切换 / 全盘扫描等）？若是，暂缓。
