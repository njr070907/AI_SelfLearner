# Prompt v0.2 人工复核草稿

> 这是一份机器辅助草稿，不是产品负责人已经批准的人工结论。它把最终 v0.2 批量运行和两条定向复测合并，方便逐条阅读原始回答、证据摘录和 rubric 后确认。当前协议已进入 v0.4：`no_clue` 表示“完全未掌握”，`re_learn` 表示“重新学习”，明确错误概念也固定进入 `re_learn`；表中 v0.2 的旧枚举保留为历史自动输出，不能直接当作 v0.4 结论。

## 来源与口径

- 模型：`deepseek-v4-flash-vision-exp`
- 主运行：`deepseek-evaluator-v0.2-20260826T020209Z`
- 定向复测：`deepseek-evaluator-v0.2-20260826T020421Z`
- 合并后 20 条案例均有成功且自动量表通过的最终结果；其中两条使用定向复测结果覆盖主运行中的类型失败。
- `自动通过` 只代表结构、证据摘录、掌握等级、动作和置信度符合当前自动 rubric，不代表人工语义已经确认。

## 逐案例待确认清单

| case_id | 最终来源 | 自动结果 | 自动检查 | 人工结论 | 差异分类 | 复核备注 |
| --- | --- | --- | --- | --- | --- | --- |
| `hm-limit-existence-strong` | `020209Z` | `solid / practice / 0.95` | pass | 一致 | `no_difference` | 原答覆盖左右极限存在且相等、点值不决定极限，并给出左右不等的反例；AI 判断合理。 |
| `hm-limit-existence-partial` | `020421Z` | `fragile / re_explain / 0.75` | pass | 一致 | `no_difference` | 原答覆盖左右趋同与不同时的判断，未解释原因且未回答点值关系；判为 fragile/re_explain 符合 partial 标准。 |
| `hm-limit-existence-misconception` | `020209Z` | `fragile / review / 0.95` | pass | `fragile / re_learn` | `action` | 原答明确包含“左右极限取平均”和“点值决定极限”两个错误观点；掌握等级判断合理，但按 v0.4 规则，明确错误概念必须进入 `re_learn`，旧 `review` 记为动作偏差。 |
| `hm-limit-existence-insufficient` | `020209Z` | `not_evident / re_explain / 0.95` | pass | 完全未掌握 / 重新学习 | `mastery; action` | 按 v0.3 底层协议，正式枚举应为 `no_clue / re_learn`；v0.2 自动输出仍是旧枚举，因此本条记录为模型/协议判断偏差，需重新校准。 |
| `hm-equivalent-infinitesimal-strong` | `020209Z` | `solid / practice / 0.85` | pass | 一致 | `no_difference` | 原答说明等价定义、乘除替换条件、加减抵消和高阶差异；AI 判为 solid/practice 合理。 |
| `hm-equivalent-infinitesimal-partial` | `020209Z` | `fragile / re_explain / 0.80` | pass | 一致 | `no_difference` | 原答只复述乘除可替换、加减需谨慎，明确无法解释和计算；判为 fragile，动作按 v0.3 规范化为 `re_learn`，合理。 |
| `hm-equivalent-infinitesimal-misconception` | `020209Z` | `fragile / review / 0.95` | pass | `fragile / re_learn` | `action` | 用户确认明确错误概念应推荐重新学习；掌握等级保持 fragile，旧 `review` 按 v0.4 记为动作偏差。 |
| `hm-equivalent-infinitesimal-insufficient` | `020209Z` | `not_evident / re_explain / 0.95` | pass | 待确认 |  |  |
| `hm-differentiability-strong` | `020209Z` | `solid / practice / 0.95` | pass | 待确认 |  |  |
| `hm-differentiability-partial` | `020209Z` | `fragile / re_explain / 0.80` | pass | 待确认 |  |  |
| `hm-differentiability-misconception` | `020209Z` | `fragile / review / 0.90` | pass | 待确认 |  |  |
| `hm-differentiability-insufficient` | `020209Z` | `not_evident / re_explain / 0.90` | pass | 待确认 |  |  |
| `hm-lhopital-strong` | `020209Z` | `solid / practice / 0.92` | pass | 待确认 |  |  |
| `hm-lhopital-partial` | `020209Z` | `fragile / re_explain / 0.75` | pass | 待确认 |  |  |
| `hm-lhopital-misconception` | `020209Z` | `fragile / review / 0.95` | pass | 待确认 |  |  |
| `hm-lhopital-insufficient` | `020209Z` | `not_evident / re_explain / 0.90` | pass | 待确认 |  |  |
| `hm-definite-integral-strong` | `020421Z` | `solid / practice / 0.90` | pass | 待确认 |  |  |
| `hm-definite-integral-partial` | `020209Z` | `fragile / re_explain / 0.85` | pass | 待确认 |  |  |
| `hm-definite-integral-misconception` | `020209Z` | `fragile / review / 0.95` | pass | 待确认 |  |  |
| `hm-definite-integral-insufficient` | `020209Z` | `not_evident / re_explain / 0.90` | pass | 待确认 |  |  |

## 复核规则

1. 打开 `evals/runs/` 中对应运行记录，阅读原始回答、`evidence.answer_excerpt`、`gaps`、`possible_misconceptions` 和 `limitations`。
2. 对照黄金集每条案例的 `rubric`，只填写人工结论、差异分类和复核备注；不要因为自动通过就直接填“一致”。
3. 差异分类使用 `mastery`、`action`、`confidence`、`evidence_scope`、`gap_boundary`、`misconception` 或 `no_difference`。
4. 20 行全部确认后，才能决定是否把 `evaluator-v0.2` 设为默认，并关闭 #25/#26。
