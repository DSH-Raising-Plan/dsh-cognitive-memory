# Memory Migration Architecture

> **轨 B / Workstream 2 · M-B Accepted（设计冻结）**  
> **依赖：** [`MEMORY_INTERCHANGE_MODEL.md`](./MEMORY_INTERCHANGE_MODEL.md) `0.1`  
> **硬规则：** 不直写核心库；不覆盖已有记忆；不自动 Active；保留来源；可回滚。

## 生命周期

```
Discover → Extract → Map(Interchange) → Preview → Plan
    → Staging → Validate → Commit | Rollback
         ↑_________________________________|  (Resume 按 batch_id)
```

| 阶段 | 职责 | 失败时 |
| --- | --- | --- |
| Discover | 用户指定 Provider + 位置；校验可达；**禁止**全盘扫描 | 中止；无副作用 |
| Extract | Adapter 分页读取 | 可重试；不写 Mnemosyne |
| Map | 转为 MIM Bundle；未知字段进 payload/extensions | 映射错误进入 Preview 报告 |
| Preview | 条数、kind 分布、冲突候选、丢失字段、样例行 | 只读 |
| Plan | `batch_id`、幂等键、冲突策略、分批大小 | 只读；可修订后重跑 |
| Staging | 写入**隔离暂存区**（非 Active / 非核心 memory 表） | 清 staging 或保留待 Resume |
| Validate | 完整性、对照 external_id、抽样 reconciliation | 阻止 Commit |
| Commit | **仅**经 Service Contract → Observation/Evidence + provenance | 见 Rollback |
| Rollback | 按 `batch_id` 撤销本批 Commit/Staging | 不影响源系统与其它批次 |
| Resume | 从最后成功 checkpoint 继续 | 幂等键防重复 |

## 批次与幂等

| 概念 | 定义 |
| --- | --- |
| `batch_id` | 一次 Plan→Commit 的唯一 ID |
| `idempotency_key` | `hash(provider, instance, external_id)`（可含内容指纹） |
| 重跑 | 相同 key 不产生第二条 Observation；更新审计计数 |
| Checkpoint | Staging 内按 chunk 记录 `offset` / `cursor` |

## Staging 模型

- 存储：独立目录或独立表前缀，例如 `migration_staging/{batch_id}/`  
- 内容：MIM 片段、identity map 草稿、校验报告、plan.json  
- **禁止：** Staging 对象被检索路径当作 Active Memory  
- Commit 成功后可归档 staging；Rollback 删除本批已提交引用并标记 `rolled_back`

## Commit 语义

```
Commit(batch) =
  for item in validated_staging:
    ServiceContract.create_observation(
      content=item.content,
      provenance=item.provenance + identity_map,
      trust=untrusted | per policy
    )
  # 永不: INSERT INTO core_active_memory ...
  # 永不: overwrite existing memory by id
```

## 冲突检测（Preview / Plan）

| 冲突类 | 策略（首阶段） |
| --- | --- |
| 同 `external_id` 已导入 | skip（默认）或 report-only |
| 内容不同、id 相同 | 标记 conflict；默认不覆盖 |
| 缺必填 MIM 字段 | 拒绝进入 Staging |
| 关系端点缺失 | 关系延期或丢弃并记入报告 |

## 校验（Validate）

1. Schema：Bundle 符合 MIM `0.1`  
2. 计数：extract ≈ mapped ≈ staged  
3. 抽样：N 条 raw_ref 可回源  
4. Identity：无重复 idempotency_key（批内）  
5. Foundation：Commit 路径只调用已发布 API  

## 回滚与恢复

| 操作 | 行为 |
| --- | --- |
| Rollback Staging | 删除 `migration_staging/{batch_id}` |
| Rollback Commit | 按 batch 审计列出的 observation ids 调用软删除/隔离 API（若无删除 API：标记 `migration_revoked` 元数据，检索排除） |
| Resume | 读取 checkpoint；跳过已成功 idempotency_key |

源系统**只读**；迁移失败不得破坏源库。

## 模块边界（实现时目录）

```
migration/
├── providers/      # registry · adapters
├── extraction/
├── interchange/    # schema · mapper
├── planning/       # preview · planner · conflict_detector
├── execution/      # staging · batch_manager · executor
├── validation/     # integrity · reconciliation
└── recovery/       # rollback · resume
```

> **本阶段只冻结设计。** 不在本提交实现引擎代码（属未来 `2.1`，且须 Design Track 退出后申请）。

## 与 Foundation 的接口

| 允许 | 禁止 |
| --- | --- |
| 调用已发布 REST / SDK（Observation 等） | 修改 Foundation REST/PCIP/Component 契约 |
| 将外源落为 Observation + provenance | 直接 INSERT 核心 memory 表 |
| Staging 使用独立存储/前缀 | 覆盖用户已有记忆 ID |

## 第一阶段范围 / 非目标

**做：** Discover → … → Commit/Rollback（设计完备；实现待 2.1）。  

**不做：** 自动切换 Agent、双向同步、自动退役旧库、未授权全盘扫描。

## 验收（设计层）— M-B

- [x] 生命周期与失败模式文档化  
- [x] Staging / Commit / Rollback 职责清晰  
- [x] 与 Interchange Schema `0.1` 对齐  
- [x] 明确「Commit = Service Contract 写入」而非 DB 直写  
- [x] 幂等键与 batch 追踪定义明确  
