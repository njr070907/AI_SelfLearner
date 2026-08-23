# Mastery Protocol

> 状态：Sprint 0 协议骨架  
> 版本：`mastery-protocol-v0.1-demo`  
> 所有者：Founder / Product Owner  
> 重要说明：当前版本只定义可实验边界，不代表掌握判断规则已经通过真实用户验证。

## 1. 为什么存在

Mastery Protocol 定义系统如何从一次及多次学习行为中形成可解释、可纠正、可重算的掌握判断。它让 Sprint 0 的工程底座直接服务于后续产品实验，避免把 LLM 的一句话直接写成用户的永久状态。

它持续回答：什么算掌握证据、什么算证据不足、遗漏与误区如何区分、何时追问或出迁移题、提示和延迟复测如何影响证据权重，以及用户纠错如何改变当前状态。

## 2. 三层职责

```text
LLM Provider
  -> Provider Observation：提取回答中的观察与证据
Mastery Engine
  -> Mastery Decision：根据协议和历史证据计算当前状态
Learning Policy
  -> Learning Action：选择一个最小下一步
```

- LLM 是传感器，不是最终裁判。
- Mastery Engine 不调用供应商 SDK，只消费已经校验的结构化观察和历史事件。
- Learning Policy 不修改历史事实，只根据当前决定选择下一步。
- UI 只展示组合后的诊断结果，不自行计算掌握状态。

## 3. Provider Observation 契约

Provider 输出必须结构化并经过 Schema 校验，至少包含：

- `evidence`：来自本次回答的最短必要证据；
- `gaps`：缺失内容及严重度；
- `possible_misconceptions`：用户明确表达的可能误区及置信度；
- `observation_confidence`：本次观察的证据充分度；
- `limitations`：当前不能可靠判断的内容；
- Provider、模型、Prompt、Schema、参数和请求版本元数据。

Provider 不直接写数据库，不更新用户状态，也不决定长期学习路径。格式无效时不得使用默认值拼出一个看似成功的结果。

## 4. Mastery Decision 契约

Mastery Engine 输出至少包含：

- `mastery_level`：`not_evident | fragile | developing | solid`；
- `understanding_level`：`novice | developing | proficient`；
- `score`：0–100 的辅助值，不作为唯一判断；
- `confidence`：结合证据数量、质量、一致性和用户反馈得出的状态置信度；
- `evidence_ids`：支持当前决定的事件或原子证据；
- `reason`：可读、可追溯的决定说明；
- `protocol_version`：生成决定的 Mastery Protocol 版本。

粗细等级映射基线：`not_evident/fragile -> novice`、`developing -> developing`、`solid -> proficient`。这只是初始兼容规则，后续必须通过评估数据修订。

## 5. Learning Action 契约

Learning Policy 只选择一个主要动作：

- `review`：复习关键内容；
- `example`：换例子或表示方式；
- `practice`：完成迁移或应用练习；
- `re_explain`：重新解释或回答追问。

每个动作包含 `instruction`、`reason`、`evidence_ids` 和策略版本。用户可以接受、跳过或纠正，跳过不能被解释为负面人格或动机证据。

## 6. 事件历史与当前状态

数据库同时保存：

1. 不可静默覆盖的学习事件，例如会话创建、回答提交、Provider 观察、失败、提示、追问、反馈和复测；
2. 可从事件重算的当前状态，例如概念掌握等级、置信度和最近证据。

回答必须先保存，再调用 Provider。失败观察不更新当前状态；用户否定的诊断保留历史，但默认不再作为确认事实参与聚合。

## 7. Sprint 0 范围

Sprint 0 只实现确定性的演示规则和 Fake 场景，用于证明完整管道、失败恢复、事件保存和重算边界。它不实现真实掌握算法，不声称能可靠评价用户。

Fake 场景至少覆盖：`strong`、`partial`、`misconception`、`insufficient_evidence`、`provider_timeout`、`provider_failure` 和 `invalid_schema`。

当无 Key 的假闭环、失败恢复、事件历史、当前状态重算和核心 CI 全部通过后，Sprint 0 立即结束，进入真实 Mastery Protocol 实验。

## 8. 变更规则

每次改变掌握含义、证据权重、等级映射、追问/迁移/复测规则或用户纠错处理时，必须：

1. 说明假设和期望改善；
2. 提升协议或相关 Schema 版本；
3. 使用同一黄金集比较新旧行为；
4. 保留旧事件和旧决定；
5. 记录采用、拒绝或回滚决定。

## 9. Sprint 1 黄金评测集

第一份固定评测集为 `high-math-mastery-v0.1`，包含 5 个高等数学知识点和 20 个原创模拟回答。每个知识点固定覆盖 `strong`、`partial`、`misconception` 和 `insufficient_evidence`，用于比较 Provider Observation、Mastery Decision 与 Learning Action 是否稳定、保守且可解释。

当前数据集状态是 `draft_human_review`。Schema 校验通过不等于数学内容已经成为黄金标准；必须由人逐项核对来源、答案类型、期望证据、误区和下一步，全部通过后才能标记为 `approved`。具体流程见 `evals/README.md`。

原始讲义 PDF 不进入仓库。评测集只保存原创案例、文件哈希与页码来源，因此它是回归测试基线，不是运行时材料库，也不会提前触发 RAG 范围。
