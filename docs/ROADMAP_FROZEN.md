# 当前路线与工程状态（正式冻结 + 双轨并行）

## 状态板

| 节点 | 状态 |
| --- | --- |
| Foundation 1.0 | **Stabilized**（契约基线 `foundation-0.1.0`） |
| Production Security Assessment | **Completed**（[`reports/PRODUCTION_SECURITY_GAP_REPORT.md`](./reports/PRODUCTION_SECURITY_GAP_REPORT.md)） |
| Production Hardening | **Deferred** |
| P3.2 | **Not Started** |
| **轨 A — Foundation 维护** | **Current** |
| **轨 B — Migration & Adoption Design** | **Started**（文档 / Schema 草案 / 样本；无引擎实现） |

## 里程碑履历

| # | 节点 | 状态 | 说明 |
| --- | --- | --- | --- |
| 1 | [#17](https://github.com/DSH-Raising-Plan/dsh-mnemosyne/pull/17) — Foundation Accepted | **Accepted** | 互操作基础可用 |
| 2 | [#18](https://github.com/DSH-Raising-Plan/dsh-mnemosyne/pull/18) — Foundation Stabilization | **Merged** | 可重复验证 / CI / 基线 |
| 3 | P3 Foundation 1.0 | **Stabilized** | `foundation-0.1.0` |
| 4 | Production Security Assessment | **Completed** | 差距报告已归档；非任务清单 |
| 5 | 稳定基线维护（轨 A） | **Current** | 契约兼容 / CI / 安全不退化 / Bug 修复 |
| 6 | Memory Migration & Adoption Design（轨 B） | **Started** | 见 [`plans/MEMORY_MIGRATION_PARALLEL_PLAN.md`](./plans/MEMORY_MIGRATION_PARALLEL_PLAN.md) |

**不自动进入 P3.2。**  
**不自动开启 Production Hardening PR。**  
**不创建** `feat/mnemosyne-2.1-memory-migration`，直至轨 B 退出条件满足。

## 双轨并行（现行）

| 轨 | 做什么 | 不做什么 |
| --- | --- | --- |
| **A** | Foundation 稳定维护 | 不主动扩张生态能力 |
| **B** | Interchange / Migration / Provider 设计与映射验证 | 不改 Foundation REST / PCIP / Component Contract；不做双向同步与完整兼容网关 |

设计文档树：

- [`architecture/MEMORY_INTERCHANGE_MODEL.md`](./architecture/MEMORY_INTERCHANGE_MODEL.md)
- [`architecture/MEMORY_MIGRATION_ARCHITECTURE.md`](./architecture/MEMORY_MIGRATION_ARCHITECTURE.md)
- [`architecture/MEMORY_ADOPTION_MODEL.md`](./architecture/MEMORY_ADOPTION_MODEL.md)
- [`architecture/MEMORY_COMPATIBILITY_ARCHITECTURE.md`](./architecture/MEMORY_COMPATIBILITY_ARCHITECTURE.md)
- [`providers/PROVIDER_CONTRACT.md`](./providers/PROVIDER_CONTRACT.md)
- [`providers/PROVIDER_MATRIX.md`](./providers/PROVIDER_MATRIX.md)
- [`providers/PROVIDER_MAPPING_GUIDE.md`](./providers/PROVIDER_MAPPING_GUIDE.md)

分支：`design/memory-interchange` · `design/memory-migration` · `research/provider-adapters`（相对 `feat/mnemosyne-2.0-p3-ecosystem`）。

## 下一步

- **轨 A：** 修阻塞复现/兼容缺陷；保持 Foundation CI 与外部探针绿灯。  
- **轨 B：** 并行推进 M-A / M-B / M-C；Interchange Contract 稳定前不正式实现 Adapter。  

重新打开加固决策的触发条件见 [`ENGINEERING_CONSTRAINTS.md`](./ENGINEERING_CONSTRAINTS.md)。  
三条安全原则见同文档「三条安全原则」。  
轨 B 硬约束见同文档「Memory Migration & Adoption」。
