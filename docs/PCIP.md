# PCIP — Personal Cognitive Interoperability Protocol（提案）

> 成熟度：**Partial**（文档 + L0–L2 stub；L3 默认拒绝；P2P/Relay Planned）  
> **不是**已有行业标准；仅为 Mnemosyne Node 间互操作草案。  
> Schema：[`schemas/pcip/exchange-v1.json`](../schemas/pcip/exchange-v1.json)

## 目标

独立 Mnemosyne Node 之间在用户授权下交换**知识投影**，而不是打开对方数据库。

## 层级

| 级别 | 内容 | 默认 |
| --- | --- | --- |
| L0 | 公开身份与能力 | 可公开 |
| L1 | 明确授权分享的知识 | 按授权 |
| L2 | 指定主题的经验与策略 | 按授权 |
| L3 | 私人经历 / 原始记忆 / 敏感信息 | **默认禁止** |

## 每次交换必须声明

- `allow_store` / `allow_forward` / `allow_train`
- 有效期、主题范围、来源节点、接收节点
- 撤销状态

## 接收规则（硬性）

外来内容进入本地后首先是 **Observation**（`provenance.trust=authorized_peer|untrusted`），  
**不得**直接写成 Active Memory。须经 Evidence 与晋升策略重新评估。

## 非目标（本阶段）

- 公共 Discovery / Relay 托管私人记忆
- 默认开启跨用户分享
- 实现完整 P2P 传输栈（Planned）
