# 真实语义验收中间校准报告

> 本报告只分析已经存在的本地脱敏运行记录，不会发起新的 Provider 调用。
> 它是自动结果与黄金量表的对照，不等于产品负责人完成了逐条人工语义复核。

## 运行范围

- 运行记录：`deepseek-evaluator-v0.1-20260824T015320Z`
- Provider：`deepseek`
- 模型：`deepseek-v4-flash-vision-exp`
- Prompt：`evaluator-v0.1`
- 案例数：20
- 自动重试：0
- 结构成功：20/20
- 自动量表通过：17/20
- 需要人工复核：20/20

## 自动失败摘要

| case_id | 自动判断 | 黄金量表要求 | 失败维度 | 初步解释 |
| --- | --- | --- | --- | --- |
| `hm-equivalent-infinitesimal-strong` | `fragile / re_explain` | `solid / practice` | 掌握等级、推荐动作 | 强答案被判断为仍需重新解释，属于边界覆盖或额外 gap 判断问题 |
| `hm-equivalent-infinitesimal-insufficient` | `not_evident / re_explain` | 掌握等级和动作符合；置信度不在量表范围 | 置信度 | 结论方向正确，但置信度校准偏离量表边界 |
| `hm-differentiability-partial` | `fragile / re_explain` | 掌握等级和动作符合；置信度不在量表范围 | 置信度 | 结论方向正确，但置信度偏高，仍需校准区间 |

## 当前结论

1. Provider 调用、JSON 解析、Schema 校验和证据摘录在本轮没有失败。
2. 主要风险集中在“强答案是否足够完整”和“证据不足/部分理解的置信度边界”。
3. `17/20` 只能作为这一轮自动量表结果，不能直接当作掌握度准确率，也不能替代人工语义结论。
4. 在人工复核和受控 Prompt v0.2 对照实验完成前，不把 `evaluator-v0.2` 设为默认，也不关闭 #24–#26。

## 下一步验收入口

- 使用 [`MANUAL_REVIEW_WORKSHEET.md`](MANUAL_REVIEW_WORKSHEET.md) 逐条对照 20 个案例的 `rubric`，记录人工结论与自动结论是否一致。
- 将差异归类为：掌握等级、推荐动作、置信度、证据范围、误区/缺口边界。
- 先用 Fake/dry-run 验证 Prompt v0.2 的变化，再由负责人明确授权后进行最小真实样本对照。
- 只有校准结果和发布边界都通过，才更新阶段 5 完成度并关闭 #24–#26。
