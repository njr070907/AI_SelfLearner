# Cognitive Engine 算法 v0.1

## 1. 目标

把多次学习事件转换为保守、可解释、可重算的知识状态和候选认知模式。算法不追求“精确测量人”，而追求比单次聊天更可靠的学习决策支持。

## 2. 输入

每次 `DiagnosisEvidence` 包含：

- 概念、问题类型与难度；
- 分维度得分和掌握等级；
- 正确点、缺失点、误区；
- 诊断证据与模型置信度；
- 是否有材料参考、追问验证；
- 用户反馈；
- Prompt/模型/Schema 版本；
- 时间。

## 3. 知识状态更新

### 3.1 证据质量

可定义：

```text
evidence_quality =
  reference_quality
× task_diagnosticity
× model_confidence
× feedback_factor
```

所有因子归一化到 0–1，并保留分项，避免黑盒总权重。

示例：有材料参考、开放机制题、经过追问且用户认可的诊断权重较高；极短回答、无参考、低置信度诊断权重较低。

### 3.2 简化状态

MVP 可维护一个 0–100 内部状态，但 UI 主要展示等级：

```text
new_score = old_score + alpha × evidence_quality × (observed_score - old_score)
```

`alpha` 初期取固定小值并由配置管理。首次证据以较低初始置信度建立状态，不把一个高分等同于稳定掌握。

### 3.3 置信度

```text
confidence = f(
  effective_sample_size,
  evidence_quality,
  consistency,
  task_diversity,
  recency
)
```

概念状态高但只有一次证据时，可以显示“表现良好，证据有限”。

## 4. 遗忘与时间

v0.1 不假装拥有精确个人遗忘曲线。时间只用于：

- 降低旧证据对“当前状态”的权重；
- 标记超过复测窗口的状态为需验证；
- 建议一次主动回忆。

有足够重复复测数据后，再拟合个体保持参数。

## 5. 误区处理

误区记录条件：用户明确表达了可判定为错误的命题。记录：类型、原句、正确对照、来源、诊断置信度、出现次数、最后时间和是否已修正。

状态转换：

```text
observed → repeated → challenged → corrected → resurfaced
```

“没有提到某点”只进入 `missing_points`，不能进入误区。

## 6. 模式发现

候选模式来自跨会话标签聚合，例如：

- 忽略适用条件；
- 把相关性当因果；
- 只描述结果、不解释机制；
- 能理解抽象但难以给出应用。

建立候选模式至少需要：

- 两次独立会话；
- 最好跨两个概念；
- 证据质量超过最低阈值；
- 没有大量反证。

向用户展示较强模式前建议至少 3 条独立证据，并允许确认。

## 7. 正反证据

每个模式维护：

```text
support_score = Σ support_weight
counter_score = Σ counter_weight
confidence = calibrated(support_score, counter_score, diversity, recency)
```

反证不能被平均掉而消失。报告应说明：“在理论解释中多次出现，但在项目案例中未出现”。

## 8. 用户反馈更新

- `accurate`：提高证据可用性，但不自动提高知识掌握分；
- `partial`：保留诊断并标记需拆分；
- `inaccurate`：降低派生结论权重，进入人工/Prompt 复核集；
- 用户说明作为单独证据，不改写原回答。

## 9. 推荐接口

Cognitive Engine 输出给推荐器：

```json
{
  "concept_state": {},
  "active_misconceptions": [],
  "missing_prerequisites": [],
  "evidence_gaps": [],
  "candidate_patterns": [],
  "recommended_review_window": null,
  "state_version": "cognitive-v0.1"
}
```

## 10. 可重算性

所有状态都是派生数据。算法升级时从不可变诊断证据重算，并保留新旧版本比较。不得只保存最终画像而丢弃来源。

## 11. 校准与验证

- 用人工标签比较状态方向是否合理；
- 检查置信度分桶与错误率；
- 测试一次异常诊断是否过度改变历史；
- 测试反证是否能降低模式置信度；
- 测试删除记录后派生状态能正确重算；
- 不把 70 与 72 的小差异当成真实变化。

## 12. 暂不实现

- 精确遗忘预测；
- 心理学人格模型；
- 跨用户规范化能力排名；
- 黑盒深度模型直接生成长期画像；
- 自动高影响人生建议。

