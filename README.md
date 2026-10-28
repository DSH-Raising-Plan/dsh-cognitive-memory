# dsh-cognitive-memory

DeepSeek Harness **认知记忆**插件：拉起外置 **cognitive-memory** 子进程，用 REST 暴露检索 / 上下文 / 观察 / 反馈工具。

面向 DeepSeek Harness / **丛雨桌宠（DSH）**。当前默认当 **副记忆（与 A-MEM 并行）**，不建议一上来就关掉旧记忆。

> 社区插件，与 DeepSeek 官方无关。  
> 英文简版：[README.en.md](./README.en.md)  
> **试用立场与转正门槛**：[TRIAL.md](./TRIAL.md)

本仓库为 **完整包**：根目录是 DSH Host Adapter；[`service/`](./service) 为 Python 认知记忆服务；[`docs/`](./docs) 为规格与排期。也可在桌宠 monorepo 中与 `services/cognitive-memory` 联调。

算法优化清单与排期：[ROADMAP.md](./ROADMAP.md) · 状态机：[docs/COGNITIVE_MEMORY_STATE_MACHINE.md](./docs/COGNITIVE_MEMORY_STATE_MACHINE.md)

### 核心链路

```
原始事件 → 短期缓冲 → 事件关联 → 情节记忆 → 行为模式 → 记忆筛选 → 长期记忆 → 用户模型
```

视频：`runStoryboard → 片段与时间戳 → 主题/实体 → 临时记忆 → 跨来源兴趣 → 长期记忆`

优化焦点不是继续加层，而是：**值得记什么、如何组成经历、何种证据够晋升、冲突如何更新、如何改善行为、如何证明有效**。

---

## 作用：它想成就怎样的 DSH

若目标是让 DSH 逐渐朝着 **「像真人一样生活、记忆、成长、形成个性，并主动与你相处」** 发展，本方案提供的不是「多记一点摘要」，而是：

> 从一个「接收指令 → 调模型 → 生成回答」的 AI，变成具有 **连续经历、稳定人格空间、动态兴趣、行为习惯与关系历史** 的数字角色。

记忆架构本身只解决「经历如何被记录、关联、晋升、纠错」；情绪、目标、Live2D 表现等仍需独立模块。但它是后者能够长期一致的基础。

优势分两层：**架构能提供什么**，以及 **如何逼近真人表现**。

---

## 一、最重要的优势：连续的生活经历

### 1. 从「每次重新认识你」到「共同生活的连续性」

普通 AI 常记得结论，却不记得事情如何发生。本方案把视频观看、日常对话、游戏体验、用户反馈等写成 **观察（observation）**，再沉淀为 **情节记忆（episode）**。

例如：不只知道你喜欢某个游戏，还能记得何时聊过、当时反应、后来有没有续谈。

**拟人化价值**：对话建立在共同经历上，而不只是机械调用资料卡。

### 2. 从「知识库」到「逐渐形成自己的兴趣」

短期观察 → 事件关联 → 兴趣候选 → 长期晋升，使兴趣随 **反复接触、主动探索、明确反馈** 调整，而不是开发者写死，也不是单次聊天定终身。

**拟人化价值**：兴趣可以随经历缓慢变化，且每次变化最好留有依据。

### 3. 从「知道事实」到「理解来龙去脉」

保留事件、时间、实体关联与原始证据，才能区分：发生了什么、当时上下文、与过去哪些经历有关、后续是否改写了理解。

**拟人化价值**：能回顾、理解变化、修正误解，而不是每次从孤立事实重推。

### 4. 从「被动回答」到「基于经历主动发起」

当话题贴近近期经历、未完成事件或长期兴趣时，上层策略可以决定是否主动提起（问项目进展、续谈某部作品等）。

**拟人化价值**：交流不再完全依赖用户提问，而呈现持续关注与话题延续。

共同点：**记忆不是仓库，而是后续理解与行为的依据。**

---

## 二、相对普通桌宠 AI 的能力对照

| 能力维度 | 普通 AI 桌宠常见做法 | 本方案方向 |
| --- | --- | --- |
| 记忆 | 聊天摘要 / 用户偏好 | 经历、证据、关联与后续变化 |
| 个性 | 固定人设提示词 | 基础人格稳定，兴趣与习惯可演化 |
| 兴趣 | 当前对话临时判断 | 长期行为、重复接触、主动参与综合判断 |
| 情绪表现 | 按当前消息生成 | 结合近期事件、持续状态、历史互动（需状态模块） |
| 主动性 | 定时 / 随机触发 | 按记忆、兴趣、未完成事件与环境决策（需决策模块） |
| 学习 | 每轮重推，偶更摘要 | 候选 → 验证 → 巩固 → 修正 → 遗忘闭环 |
| 自我一致性 | 主要靠提示词 | 人格边界 + 习惯 + 历史经历共同约束 |

**强调**：记忆服务为这些能力提供底座，**不会自动生成**完整情绪、人格或自主意识；那些仍需独立的状态模型、决策与行为系统。

---

## 三、最值得投入的三个技术优势

### 1. 记忆与行为形成闭环

```
感知与观察          认知与记忆              状态与决策              行为与反馈
聊天 / 视频 / 游戏   事件关联 · 兴趣判断      情绪 · 目标 · 关系       主动聊 · 探索 · 习惯调整
桌面 / 用户行为  →  情节 · 长期知识     →   注意力 · 行为选择  →  结果再变观察 ──┘
```

比「更聪明的记忆库」更重要的是：行为结果重新成为观察，影响后续记忆与决策。

例：常主动聊某主题且你积极回应 → 提高该主题被提起的优先级；多次冷淡 → 降低。  
同时 **分开记录**：角色内部兴趣、用户兴趣、双方互动反馈——勿把用户回应直接等同于角色喜好。

### 2. 人格稳定但不僵化

| 层次 | 内容 | 更新节奏 |
| --- | --- | --- |
| **基础人格层** | 性格倾向、表达风格、价值偏好、角色边界 | 相对稳定，不因一两轮对话改写 |
| **经验塑造层** | 兴趣、熟悉度、行为习惯、话题态度 | 随经历缓慢更新，保留变化依据 |
| **动态状态层** | 当前情绪、注意力、疲劳模拟、近期关注 | 短期波动，可随时间/事件恢复 |

避免：人格固化（只会换说法重复人设）、人格漂移（一段对话突然改长期立场）。  
这是面向工程的分层，受心理学启发，**不等于**完整复现人类心理。

### 3. 可追溯的成长历史

每次兴趣/长期判断更新都应能说明依据，例如：

- 10/01 首次接触某游戏 → 10/05 多次相关视频 → 10/08 主动讨论机制  
- 10/12 候选「可能感兴趣」→ 10/20 证据加分提高置信度 → 11/03 信号变化，降低主动推荐

好处：

1. **纠错**：用户纠正后能定位受影响记忆，而不只覆盖摘要  
2. **解释**：能说明「为什么认为这件事重要」  
3. **回滚**：错误推断 / 错误长期记忆可撤销  
4. **评估**：哪些观察信号真正改善了后续行为  

长期桌宠若无来源、版本与修正机制，错误记忆会持续污染推理。

---

## 四、单靠记忆还缺什么（真人化补齐清单）

| 模块 | 作用 |
| --- | --- |
| **情绪动力** | 短期情绪、触发、变化速度与恢复；影响表达与注意力，而非提示词里写「表现开心」 |
| **目标与动机** | 短/长期目标、好奇心、待解决问题、行动优先级；避免主动性退化为随机找话题 |
| **时间与日常** | 时间流逝、活动阶段、事件间隔、任务进度；无对话时仍维持合理状态 |
| **社交与关系** | 共同经历、沟通偏好、承诺、冲突、反馈与边界；勿把回应一律当成情感认同 |
| **感知与动作** | 视频/桌面感知与 Live2D 表情、口型、动作打通，让内在状态外显 |

---

## 五、推进顺序：先「持续变化」，再「像真人说话」

拟人化五阶段仍适用。工程排期 **P0–P3**（详见 [ROADMAP.md](./ROADMAP.md)）：

| 阶段 | 内容 |
| --- | --- |
| **P0** | Observation / Episode / Candidate / Memory / Evidence；晋升·失效·纠正；决策日志与算法版本 |
| **P1** | Graphiti 时间图谱 + 混合检索；SQLite 证据与任务底座；REST/MCP 与失败恢复 |
| **P2** | `runStoryboard`；观看行为与内容分模；临时记忆；跨来源兴趣；`UNKNOWN→WEAK_SIGNAL→CANDIDATE→CONFIRMED` |
| **P3** | 空闲巩固；策略实验；固定测试集验证准确性 / 纠错 / 主动收益 |

兴趣证据分层（勿混成单一分数）：**被动暴露 / 注意力 / 主动参与 / 明确反馈**。  
复用 Graphiti / Cognee / Mem0 / Letta 的基础设施与流程思想；**状态机、证据权重、何时主动互动必须自研**，阈值靠实验。

**优先打通**：情节记忆 + 证据分层的动态兴趣 + 行为反馈闭环。

### 最终判断

最大优势：提供 **从经历形成认知 → 认知影响行为 → 行为反馈继续成长** 的基础。  
最值得追求的不是生成「我今天很开心」的句子，而是根据此前发生的事表现出合理状态变化，并在未来行为中持续体现。  

这提高的是 **功能层面的真人感与长期一致性**，不能据此声称真实主观体验或意识。

---

## 本仓库结构（以及为什么这样拆）

```
dsh-cognitive-memory/
├── dsh.plugin.json       # DSH 插件清单（inject: tools）
├── cordis.patch.yml
├── package.json
├── src/                  # Host Adapter
├── service/              # Python cognitive-memory（MemoryService）
├── docs/                 # SPEC · ROADMAP · STATE_MACHINE
├── ROADMAP.md
├── README.md
└── LICENSE
```

与 Python 服务的分工：

| 层 | 职责 |
| --- | --- |
| **本插件（Host Adapter）** | 发现/启动服务、鉴权、把能力暴露成 DSH tools |
| **cognitive-memory 服务** | `MemoryService`：观察/记忆/检索/晋升/Outbox；REST = MCP |
| **桌宠 bridge**（monorepo） | 对话编排与 gatekeeper 注入；视频 episode → observation |

| 选择 | 理由 |
| --- | --- |
| **独立子进程** | 记忆崩溃不拖垮对话；可单独升级、备份、限权 |
| **插件只做 Adapter** | 认知逻辑留在 Python；Harness 与桌宠共用同一服务 |
| **一个 Service，REST = MCP** | 协议稳定、算法可换；避免两套语义漂移 |
| **观察 ≠ 记忆** | 原始经历可追溯；晋升后的断言可纠错、可回滚 |
| **快 / 慢双通道** | 对话不堵在归纳上；慢任务 Outbox/Tasks 可恢复 |
| **tool-spec 与 execute 分离** | 契约给模型看，实现可独立演进 |
| **SQLite + FTS5（服务侧）** | 本机单用户够用、可离线备份；检索可降级 LIKE |

### 五条底线（服务侧）

1. 一个业务核心，两个对外入口（MCP = REST）。  
2. 观察 ≠ 记忆，推断 ≠ 事实。  
3. 事件必须能恢复（Outbox/Tasks 落库）。  
4. 检索可降级（FTS 失败回退 LIKE）。  
5. 先稳定协议，再扩展算法。

---

## 安装

需本机 Python ≥ 3.11。仓库 **必须带 `service/`**（完整包）；Host Adapter 会向上查找 `service/src/cognitive_memory/main.py`，**不再依赖** monorepo 的 `../../../services/cognitive-memory` 才能起。

```bash
# 建议：本地克隆完整仓库再装（保证 service/ 在插件旁）
git clone -b plugin/dsh https://github.com/DSH-Raising-Plan/dsh-cognitive-memory.git
cd dsh-cognitive-memory
pip install -e ./service
dsh plugin --profile web add ./   # 或 add github:...#plugin/dsh 后确认安装目录里仍有 service/
```

若 `dsh plugin add github:...` 后启动报「Python service not found」，说明安装树没带上 `service/`：改用本地路径安装，或设 `DSH_COGNITIVE_MEMORY_ROOT` / `service_root`。

桌宠侧默认 **`replace_a_mem: false`**（副记忆并行）。见 [TRIAL.md](./TRIAL.md)。

### 备份 / 迁移

```bash
python -m cognitive_memory.cli backup
python -m cognitive_memory.cli restore path/to/memory-….db --force
python -m cognitive_memory.cli migrate-amem --jsonl export.jsonl
# Windows 日备：pwsh scripts/backup-daily.ps1
```

---

## 工具

| 工具 | 作用 |
| --- | --- |
| `memory_health` | 健康检查 |
| `memory_search` | 搜索记忆 |
| `memory_get` | 详情 + 证据 |
| `memory_context` | 组装上下文（快速通道） |
| `memory_propose` | 提交候选记忆 |
| `memory_observe` | 提交原始观察 |
| `memory_feedback` | 有用/有误反馈 |
| `memory_update` / `memory_forget` | 更新 / 失效 |
| `memory_task_status` | 后台任务 |

---

## 配置（cordis）

```yaml
dsh-cognitive-memory:
  auto_start: true
  # service_root: D:/path/to/services/cognitive-memory
  # data_dir: C:/Users/.../AppData/Local/DSH/cognitive-memory
  # token: 可选；不设则自动生成并写入 runtime/token
  # base_url: 若服务已外部启动，可只填 base_url + token
```

数据目录（Windows，服务默认）：`%LOCALAPPDATA%/DSH/cognitive-memory/`

---

## 许可

AGPL-3.0-or-later
