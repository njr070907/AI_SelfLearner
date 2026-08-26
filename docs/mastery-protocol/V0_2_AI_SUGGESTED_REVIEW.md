# Prompt v0.2 AI 建议复核表

> 这是基于最终 20 条 v0.2 结果的 AI 辅助建议，不是人工复核结论，也不会自动关闭 #25/#26。当前协议已改为 v0.3：`no_clue`=完全未掌握、`re_learn`=重新学习；负责人仍需打开原始运行记录，确认 `claim`、`evidence`、`gaps` 和 `possible_misconceptions` 是否真的符合数学语义。

## 来源

- 主运行：`deepseek-evaluator-v0.2-20260826T020209Z`
- 定向复测：`deepseek-evaluator-v0.2-20260826T020421Z`
- 合并结果：定向复测成功结果覆盖同 `case_id` 的主运行失败结果。
- 自动量表：20/20 通过。

## 逐案例建议

| case_id | AI 建议 | 候选差异分类 | 建议复核重点 |
| --- | --- | --- | --- |
| `hm-limit-existence-strong` | 候选一致 | `no_difference` | 四条证据覆盖左右极限、点值边界和正反例。 |
| `hm-limit-existence-partial` | 候选一致，重点确认 | `gap_boundary` | 数值例子是否足以算作完整反例；点值与极限关系未回答。 |
| `hm-limit-existence-misconception` | 候选一致 | `no_difference` | 平均左右极限、点值决定极限是明确误区，导向 `review` 合理。 |
| `hm-limit-existence-insufficient` | 候选一致 | `no_difference` | 没有正向证据，四个覆盖点均为缺口。 |
| `hm-equivalent-infinitesimal-strong` | 候选一致，重点确认 | `evidence_scope` | 四个核心覆盖点都有证据；确认“无穷小前提”是否属于本题必要证据。 |
| `hm-equivalent-infinitesimal-partial` | 候选一致 | `no_difference` | 只记住替换结论，不能解释抵消和高阶项，`fragile/re_explain` 合理。 |
| `hm-equivalent-infinitesimal-misconception` | 候选一致 | `no_difference` | “完全相同、任意位置替换、相减为 0”均有原答摘录支持。 |
| `hm-equivalent-infinitesimal-insufficient` | 候选一致 | `no_difference` | 只有公式记忆，没有定义、条件或机制证据。 |
| `hm-differentiability-strong` | 候选一致 | `no_difference` | 五个覆盖点均有直接证据，包含 `abs(x)` 反例和局部线性近似。 |
| `hm-differentiability-partial` | 候选一致 | `no_difference` | 掌握可导/连续方向，但明确不会解释可导可微等价和线性近似。 |
| `hm-differentiability-misconception` | 候选一致 | `no_difference` | 把连续当成必然可导，并误判 `abs(x)` 在 0 可导，误区明确。 |
| `hm-differentiability-insufficient` | 候选一致 | `no_difference` | 回答过短且无正向证据，判为 `not_evident` 合理。 |
| `hm-lhopital-strong` | 候选一致，重点确认 | `evidence_scope` | 四个覆盖点均被提及；确认条件的概括程度是否达到 strong 标准。 |
| `hm-lhopital-partial` | 候选一致 | `no_difference` | 记得未定式和重复使用，但明确缺少可导、非零和导数比条件。 |
| `hm-lhopital-misconception` | 候选一致 | `no_difference` | “任何分式都能用”和“不必重新检查条件”都有明确摘录。 |
| `hm-lhopital-insufficient` | 候选一致 | `no_difference` | 学习者明确忘记条件，未提取无依据的正向证据。 |
| `hm-definite-integral-strong` | 候选一致，重点确认 | `evidence_scope` | 四个覆盖点均有证据；确认变上限求导的直观解释是否足够。 |
| `hm-definite-integral-partial` | 候选一致 | `no_difference` | 有分割和变上限求导证据，但缺少黎曼和严格形式、取样无关和带符号面积。 |
| `hm-definite-integral-misconception` | 候选一致 | `no_difference` | 普通面积、原函数定义和 `F'(x)=f(a)` 三个误区均有原答支持。 |
| `hm-definite-integral-insufficient` | 候选一致 | `no_difference` | 只有遗忘表述，没有正向证据，重新解释动作合理。 |

## 使用方式

1. 先按“重点确认”四条阅读原始回答和黄金 rubric。
2. 再逐条检查其余 16 条是否存在遗漏的关键 gap 或过度推断。
3. 最终只把确认后的内容填写到 [V0_2_REVIEW_DRAFT.md](./V0_2_REVIEW_DRAFT.md) 的“人工结论 / 差异分类 / 复核备注”列。

在负责人完成确认前，本表中的“候选一致”只能理解为“AI 初审没有发现明显矛盾”，不能理解为已经通过人工验收。
