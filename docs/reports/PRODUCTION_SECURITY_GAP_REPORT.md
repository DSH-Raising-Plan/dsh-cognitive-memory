# Production Security Gap Report

> **性质：** 风险差距报告（非开发任务列表、非加固 PR）  
> **范围：** Foundation 1.0（`foundation-0.1.0`）稳定后的生产安全条件判断  
> **约束：** [`ENGINEERING_CONSTRAINTS.md`](../ENGINEERING_CONSTRAINTS.md)  
> **日期：** 2026-10-30  
> **结论先行：** 在「本机环回 + 单用户持有 Bearer + 不开放跨节点联邦」条件下，Foundation 可作为**个人节点互操作基线**使用；在「远程可达 API / 多租户 / 跨节点信任交换」条件下，**尚不能安全地按生产标准开放**。

---

## 0. 执行摘要

| 议题 | 结论类别 | 生产发布阻断？ |
| --- | --- | --- |
| A. 本地 Bearer 全权模式（`require_component=false`） | **条件性修复** | 仅当 API 对不可信网络暴露时为阻断 |
| B. 节点密码学身份 | **条件性修复** | 仅当启用跨节点 / 互信 PCIP 时为阻断 |
| C. `allow_train` / `allow_forward` 深层执法 | **条件性修复** | 仅当存在训练出口或再分发通道时为阻断 |
| D. P2P / Relay 安全边界 | **暂缓** | 当前无实现面；启用前必须专项评估（届时可能升为阻断） |

**三类结论定义（本报告统一使用）：**

- **必须修复：** 存在明确安全风险，不能仅靠文档/运维约定规避。  
- **条件性修复：** 仅在开放远程访问、跨节点联邦等场景启用前必须解决。  
- **暂缓：** 当前 Foundation 默认使用场景下风险可接受，未来有实际需求再处理。

本报告**不**把「条件性修复」自动翻译成下一迭代的模块清单。

---

## 1. 当前实现与证据

### 1.1 部署与信任默认值

| 项 | 实现 | 证据 |
| --- | --- | --- |
| 默认监听 | `127.0.0.1` | `service/src/mnemosyne/main.py` / `bootstrap.py`（`DSH_MEMORY_HOST` 默认环回） |
| API 认证 | 单一 Bearer（`Authorization` 或 `X-Memory-Token`） | `create_app` → `require_token` |
| 组件强制 | 默认 **关闭** | `require_component: bool = False` |
| 无 Component 时 | `legacy_token_only` **放行** | `component_auth.check_component_access` |
| Discovery 联邦声明 | `local_api_only` stub | `GET /api/v1/discovery` → `federation.transport` |

### 1.2 已验证的 Foundation 安全相关控制

| 控制 | 行为 | 测试 / 探针证据 |
| --- | --- | --- |
| L3 默认拒绝 | PCIP L3 → 403 / `l3_forbidden_by_default` | `test_pcip_federation`；外部探针 `pcip.l3_denied` |
| 入站仅 Observation | 不自动 Active semantic | `test_pcip_federation`；探针 `no_auto_active_semantic` |
| 入站信任标记 | `trust=untrusted`（stub，无对等认证） | `pcip.accept_inbound_exchange`；探针 |
| 过期策略 | `policy_expired` | unit + 探针 |
| 错目标节点 | `to_node_mismatch` | unit + 探针 |
| Route scopes | discovery / PCIP / register 已映射 | `component_auth.ROUTE_SCOPES`；`test_foundation_compat` |
| 自助注册钳制 | scopes ⊆ `ALL_SCOPES ∩ capabilities`，禁 `*` | `components/register` |
| 契约基线 | `foundation-0.1.0` / CI `foundation-stabilization` | `schemas/VERSIONS.json`；#18 CI |

### 1.3 配置面（与风险相关）

- 单 Node、单 `access_token`：持有者即等价于该 Node 的管理员平面。  
- PCIP 目前挂在**同一 REST API** 上，不存在独立对等传输栈。  
- Schema 中的 `allow_store` / `allow_forward` / `allow_train` **有字段、有校验类型**；接受路径**未**按字段做出口/训练侧执法。

---

## 2. 威胁场景与攻击面

假定攻击者目标：读取/篡改个人记忆、注入伪事实、绕过隔离、或在联邦场景下冒充对等节点。

| ID | 威胁场景 | 攻击面入口 | 前置条件 |
| --- | --- | --- | --- |
| T1 | 窃取或猜测 Bearer 后任意读写记忆 / 接受 PCIP | REST `/api/v1/*` | Token 泄露；或 API 绑定非本机且无额外网络控制 |
| T2 | 用 token 自助注册组件并扩大可用操作面 | `POST /components/register` + 后续带 `X-Component-Id` | Token 有效；scopes 钳制仍受 ALL_SCOPES 上限约束 |
| T3 | 在 `require_component=false` 下完全不带 Component，仅凭 token 调用 | 全 API | 默认配置 |
| T4 | 伪造 PCIP 入站，注入 Observation 内容 | `POST /pcip/exchange/accept` | 能调用该 API（即具备 token 或等价访问） |
| T5 | 宣称 `allow_train=false` 但仍被下游训练管道消费 | 任何读取 Observation/记忆并外送训练的集成 | 存在训练/导出通道且不读 policy |
| T6 | 宣称 `allow_forward=false` 但仍被转发到他节点 | 未来 Relay / 出站 PCIP / 人工导出 | 存在再分发通道 |
| T7 | 跨节点场景下无密码学身份，信任仅靠「能打到 API」 | 联邦 / 公网暴露 | 非当前默认；若启用则面积极大 |
| T8 | P2P/Relay 引入后的新传输与发现面 | 尚不存在 | 仅当实现并开启 |

**当前默认攻击面收缩因素：** 环回绑定 + 单用户持有 token + 无 P2P。  
**当前默认攻击面放大因素：** 单一共享密钥；组件授权默认不强制；PCIP 与业务 API 同平面。

---

## 3. 已有控制措施及其有效性

| 控制 | 对抗 | 有效性（默认部署） | 有效性（远程/联邦） |
| --- | --- | --- | --- |
| 环回绑定 | 远程直连 | **高**（依赖运维不改 `0.0.0.0`） | **失效** |
| Bearer 机密性 | 未授权调用 | **中**（单密钥、无轮换/无绑定设备） | **低** |
| Component scopes | 最小权限组件 | **中**（仅当启用并强制 Component） | 同左；默认关闭则**不生效** |
| L3 拒绝 | 私人记忆交换 | **高**（代码路径硬拒） | **高**（同路径） |
| Observation 隔离 | 外部内容直接变事实 | **高**（不自动 Active semantic） | **高**（仍可污染 Observation 层） |
| `trust=untrusted` | 误信对等 | **低–中**（标记存在，无强制晋升门闸以外的密码学） | **低**（可被有 API 权限者随意写入） |
| policy 过期 / to_node | 过期或错投交换 | **高**（针对已声明字段） | **高** |
| allow_train/forward 字段 | 训练/转发滥用 | **低**（仅 schema 声明） | **低** |
| Discovery `local_api_only` | 误以为有中继 | **文档/发现信号**（非强制执行器） | 不构成控制 |

---

## 4. 未关闭风险及可利用条件

### A. 本地 Bearer 全权模式（L-02）

- **未关闭点：** `require_component=false` 时，有效 Bearer ≈ Node 全权；无 Component 亦放行。  
- **可利用条件：**（1）token 泄露给恶意进程/用户；（2）服务绑定到非环回且网络可达；（3）多应用共享同一 token。  
- **不能靠文档单独消除的部分：** 一旦 API 可达且 token 泄露，攻击者无需再突破其他应用层门闩。

### B. 节点密码学身份（L-03）

- **未关闭点：** `from_node` 等为自由字符串；无签名、无密钥目录、无挑战应答。  
- **可利用条件：** 调用方已具备对本 Node PCIP accept（或等价）的 API 访问。  
- **在默认本机模型下：** 伪造「对等节点」与「本机恶意调用者」等价，额外身份层收益有限。  
- **在跨节点模型下：** 无身份则无法区分授权对等与滥用 token 的注入者。

### C. `allow_train` / `allow_forward` 深层执法（L-04）

- **未关闭点：** 接受时写入 Observation；policy 存 metadata，但无统一出口检查点拒绝训练/转发。  
- **可利用条件：** 存在读取记忆/Observation 并送往训练或他节点的集成，且该集成不尊重 metadata.policy。  
- **Foundation 内：** 无内置训练管道、无 Relay；风险主要在**未来集成**。

### D. P2P / Relay 安全边界（L-05）

- **未关闭点：** 功能未实现 → **无运行时攻击面**，但亦无现成安全边界设计落地。  
- **可利用条件：** 仅当引入发现、中继、多跳转发后。  
- **当前：** 风险为「过早实现会带入未评估面」，而非「现网可被利用」。

---

## 5. 风险等级、影响范围、发生可能性

评级说明（本报告）：

- **影响：** 对机密性 / 完整性 / 可恢复性的最坏合理后果。  
- **可能性：** 在所述部署条件下，威胁前提出现的合理概率。  
- **综合：** 非 CVSS 精确分，用于发布决策。

| 议题 | 默认本机单用户 | 远程暴露 API | 跨节点联邦启用 |
| --- | --- | --- | --- |
| A Bearer 全权 | 影响高 / 可能性低→中 → **中** | 影响高 / 可能性高 → **高** | 同远程 + 共享密钥扩散 → **高** |
| B 密码学身份 | 影响低（与本机滥用同构）→ **低** | 影响中 → **中** | 影响高 / 可能性高 → **高** |
| C train/forward 执法 | 影响低（无出口）→ **低** | 影响中（若有云同步/导出）→ **中** | 影响高 → **高** |
| D P2P/Relay | 无面 → **无（暂缓）** | 无面 → **无** | 若上线未加固 → **高（未来）** |

---

## 6. 修复建议、兼容性影响、实施成本（建议级，非排期）

> 下列为评估意见，**不是**已批准的开发任务。

| 议题 | 方向性建议 | 兼容性 | 成本粗估 |
| --- | --- | --- | --- |
| A | 区分「本机开发配置档」与「生产配置档」：生产默认 `require_component=true`、禁止无 Component；可选 token 绑定 loopback-only 健康检查；文档明确「环回+单用户」安全边界 | 中：默认收紧会破坏仅靠 token 的旧客户端 → 需版本/迁移 | 中 |
| B | 仅在联邦里程碑引入节点密钥与签名交换；此前保持 `untrusted` + Observation 隔离 | 中→高：新身份字段与验签 | 高 |
| C | 在**真正存在的出口**（训练 job、出站 PCIP、导出 API）设统一 policy gate；无出口则不必虚构执法层 | 低：加法门闩 | 中（有出口时） |
| D | 不实现则不开放；若立项，单独威胁模型（发现、中继信任、多跳 allow_forward、撤销） | 高：新协议面 | 高 |

---

## 7. 是否需要修复 / 是否构成生产发布阻断

### 部署条件判定（核心问题）

| 部署条件 | 是否「足够安全」用于个人 Foundation 基线 | 阻断项 |
| --- | --- | --- |
| **本机环回 + 用户独占 Bearer + 不联邦 + 无训练/中继出口** | **是**（接受剩余条件性风险） | 无必须修复项 |
| API 绑定到局域网/公网，或 token 可能被不可信方持有 | **否** | **A 升级为发布阻断**（在暴露前） |
| 启用跨节点互信交换 / 多 Node 拓扑 | **否** | **B（及视出口情况 C）为阻断** |
| 启用训练管道或自动转发 | **否**（相对策略承诺） | **C 为阻断** |
| 启用 P2P/Relay | **否**（直至专项评估与设计落地） | **D 专项通过前阻断启用** |

### 分项结论（三类）

#### 必须修复

- **无。**  
  在「文档与默认绑定所定义的 Foundation 本机场景」下，未发现「仅靠文档无法约束、且默认配置即可被远程利用」的独立必选项。  
  （若运维违反默认——例如监听 `0.0.0.0` 且共用弱 token——属于**部署违规**，应在发布清单中列为运维阻断，而非 Foundation 契约缺陷本身。）

#### 条件性修复

| 议题 | 触发条件（满足则必须在启用前修复） |
| --- | --- |
| **A Bearer 全权** | 非环回可达、多用户共享 Node、或托管环境 |
| **B 密码学身份** | 跨节点 PCIP / 互信联邦 |
| **C train/forward 执法** | 存在训练、导出或自动转发通道，且产品声称遵守 policy |

#### 暂缓

| 议题 | 理由 |
| --- | --- |
| **D P2P / Relay 安全边界** | 无实现、无攻击面；过早建设违反「不为路线图而开发」 |
| A/B/C 在严格本机单用户场景下的增强 | 有收益但非当前阻断；可放入评估后的可选加固批次 |

---

## 8. 总判断（回答「在什么条件下已经够安全」）

**已经相对足够安全的条件（Foundation 个人节点）：**

1. 进程仅监听环回（或等价的本机 IPC）；  
2. Bearer 仅由主机用户/本机可信进程持有，不进入不可信扩展；  
3. 不宣称跨节点互信，不启用联邦传输；  
4. 不把 Observation/记忆自动送入训练或他方系统，或送入时人工负责；  
5. 保持 L3 拒绝与「外源不进 Active」等 Foundation 回归绿灯。

**尚不能安全开放的条件：**

1. 把 Memory API 暴露给局域网/公网「当云服务用」；  
2. 多租户或多不可信客户端共享同一 Node token；  
3. 跨节点自动交换且把对等当作可信身份；  
4. 产品承诺遵守 `allow_train`/`allow_forward` 却无出口执法；  
5. 上线 P2P/Relay 而未做专项安全设计。

---

## 9. 建议的下一步（仍不是 PR 列表）

1. 将本报告作为 Production Security Assessment 的基线结论归档。  
2. 若存在「计划远程暴露或联邦」的真实日程 → 再开**生产安全加固**立项，优先处理对应的条件性修复项。  
3. 若长期保持本机单用户 → **可不开发** A/B/C/D，仅加强发布/运维检查清单（绑定地址、token 保管）。  
4. **不自动开启 P3.2**；不因本报告存在「条件性修复」而默认开工。

---

## 10. 证据索引

| 类型 | 路径 |
| --- | --- |
| Auth / scopes | `service/src/mnemosyne/governance/component_auth.py` |
| API token / require_component | `service/src/mnemosyne/api/app.py` |
| PCIP stub | `service/src/mnemosyne/federation/pcip.py` |
| 默认 host | `service/src/mnemosyne/main.py`, `bootstrap.py` |
| 验收 / 限制 | `docs/P3_FOUNDATION_ACCEPTANCE.md`, `docs/FOUNDATION_KNOWN_LIMITS.md` |
| 测试 | `service/tests/unit/test_pcip_federation.py`, `test_component_auth.py`, `test_foundation_compat.py` |
| 外部探针 | `scripts/run_external_interop_probe.py`, `examples/external-weather-adapter/` |
| CI | `.github/workflows/ci.yml` → `foundation-stabilization` |
