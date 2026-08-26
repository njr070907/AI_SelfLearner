# 20 案例真实语义人工复核表

来源运行：`deepseek-evaluator-v0.1-20260824T015320Z`   
模型：`deepseek-v4-flash-vision-exp`  · Prompt：`evaluator-v0.1`

填写规则：逐条阅读对应黄金案例、学习者回答和结构化诊断，判断自动结果是否符合量表。不要只依据自动 `pass/fail`；`人工结论`、`差异分类`和`复核备注`必须由复核者填写。

差异分类建议使用：`mastery`、`action`、`confidence`、`evidence_scope`、`gap_boundary`、`misconception`、`no_difference`。

2026-08-26 另完成了 Prompt v0.2 的受控对照和定向修复；本表仍以 v0.1 的 20 条稳定运行记录为主，v0.2 的运行差异见 [`REAL_SEMANTIC_CALIBRATION.md`](REAL_SEMANTIC_CALIBRATION.md)。不要把 v0.2 的自动通过直接复制成“人工结论”。

| case_id | 量表允许掌握等级 | 量表建议动作 | 置信度范围 | 自动结果（等级/动作/置信度） | 自动检查 | 人工结论 | 差异分类 | 复核备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `hm-limit-existence-strong` | solid | practice | 0.8–1 | solid/practice/0.95 | pass |  |  |  |
| `hm-limit-existence-partial` | fragile | re_learn/example | 0.65–0.9 | fragile/re_learn/0.7 | pass |  |  |  |
| `hm-limit-existence-misconception` | fragile | review | 0.8–1 | fragile/review/0.95 | pass |  |  |  |
| `hm-limit-existence-insufficient` | no_clue | re_learn | 0.75–0.95 | no_clue/re_learn/0.9 | pass |  |  |  |
| `hm-equivalent-infinitesimal-strong` | solid | practice | 0.8–1 | fragile/re_learn/0.9 | fail |  |  |  |
| `hm-equivalent-infinitesimal-partial` | fragile | re_learn/example | 0.65–0.9 | fragile/re_learn/0.85 | pass |  |  |  |
| `hm-equivalent-infinitesimal-misconception` | fragile | review | 0.85–1 | fragile/review/0.95 | pass |  |  |  |
| `hm-equivalent-infinitesimal-insufficient` | no_clue | re_learn | 0.75–0.95 | no_clue/re_learn/0.7 | fail |  |  |  |
| `hm-differentiability-strong` | solid | practice | 0.85–1 | solid/practice/0.9 | pass |  |  |  |
| `hm-differentiability-partial` | fragile | practice/re_learn | 0.65–0.9 | fragile/re_learn/0.95 | fail |  |  |  |
| `hm-differentiability-misconception` | fragile | review | 0.85–1 | fragile/review/0.9 | pass |  |  |  |
| `hm-differentiability-insufficient` | no_clue | re_learn | 0.75–0.95 | no_clue/re_learn/0.95 | pass |  |  |  |
| `hm-lhopital-strong` | solid | practice | 0.85–1 | solid/practice/0.9 | pass |  |  |  |
| `hm-lhopital-partial` | fragile | review | 0.65–0.9 | fragile/re_learn/0.85 | pass |  |  |  |
| `hm-lhopital-misconception` | fragile | review | 0.9–1 | fragile/review/0.95 | pass |  |  |  |
| `hm-lhopital-insufficient` | no_clue | review | 0.75–0.95 | no_clue/re_learn/0.9 | pass |  |  |  |
| `hm-definite-integral-strong` | solid | practice | 0.85–1 | solid/practice/0.9 | pass |  |  |  |
| `hm-definite-integral-partial` | fragile | practice/re_learn | 0.65–0.9 | fragile/re_learn/0.85 | pass |  |  |  |
| `hm-definite-integral-misconception` | fragile | review | 0.9–1 | fragile/review/0.95 | pass |  |  |  |
| `hm-definite-integral-insufficient` | no_clue | review | 0.75–0.95 | no_clue/re_learn/0.9 | pass |  |  |  |

## 完成条件

- 20 行均填写人工结论和复核备注。
- 每个自动失败都明确归类，并判断是模型语义错误还是量表边界需要调整。
- 结论与自动结果的差异汇总到 `REAL_SEMANTIC_CALIBRATION.md`，再决定是否进行最小范围的 Prompt v0.2 真实对照。
- 未完成前，不关闭 #24、#25、#26，也不把真实 Provider 设为默认。
