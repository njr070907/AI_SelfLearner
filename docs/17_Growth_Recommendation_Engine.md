# Growth Recommendation Engine

## 1. 目的

把诊断转化为用户真正能执行的下一步。推荐不是生成一整套宏大计划，而是在当前认知状态下选择信息价值和学习价值最高的一个动作。

## 2. 输入

- 当前目标与期限；
- 当前概念及前置依赖；
- 最新诊断、误区、缺失点与置信度；
- 历史知识状态和复测时间；
- 用户可用时间、偏好与最近行动；
- 候选学习资源（若有）。

## 3. 候选行动类型

```text
clarify_definition      澄清定义
relearn_mechanism       重学核心机制
repair_misconception    修正错误认知
study_prerequisite      补前置知识
answer_follow_up        回答诊断追问
practice_transfer       做迁移应用
compare_concepts        对比易混概念
schedule_recall         安排主动回忆
advance                 进入下一知识点
seek_reference          补充权威材料
```

## 4. 排序因素

```text
priority =
  goal_relevance
× concept_importance
× dependency_impact
× diagnosis_confidence
× expected_learning_gain
× feasibility
- fatigue_cost
- repetition_cost
```

这是产品思考框架，不是假装精确的科学公式。v0.1 可使用清晰规则实现，并在实验日志中记录选择原因。

## 5. 核心规则

1. 有高置信度重大误区时，优先修正误区；
2. 缺失前置知识且阻塞多个后续概念时，优先补前置；
3. 回答证据不足时，先追问，不直接推荐重学整章；
4. 核心机制正确但无法举例时，安排迁移应用；
5. 多次表现稳定且证据充分时，进入下一概念；
6. 状态过久未验证时，安排短主动回忆；
7. 一次只给一个主行动，最多两个备选。

## 6. 输出 Schema

```json
{
  "primary_action": {
    "type": "relearn_mechanism",
    "title": "用一维图像重建梯度方向",
    "reason": "你已理解降低误差的目标，但尚未解释参数方向。",
    "evidence_ids": ["diagnosis-123"],
    "estimated_minutes": 20,
    "completion_check": "能解释梯度、负方向与学习率的关系"
  },
  "alternatives": [],
  "confidence": 0.78,
  "limitations": ["尚未测试应用能力"]
}
```

## 7. 动态难度

- 连续两次核心机制错误：降低题目范围，补前置；
- 机制正确但边界缺失：增加反例和边界题；
- 多次稳定：加入迁移和比较；
- 表现波动大：保持同难度，增加不同表达形式验证；
- 置信度低：不自动升降级，优先收集证据。

## 8. 节奏与遗忘

初期使用简单复测窗口，例如 1 天、3 天、7 天作为实验变量，不声称是用户精确遗忘曲线。根据真实复测表现调整，而不是只根据点击完成率。

## 9. 用户控制

用户可选择：接受、换一个、稍后、跳过，并可说明原因。跳过不等于懒惰；它是偏好和情境数据，不能直接进入负面画像。

## 10. 推荐质量指标

- 建议采纳率；
- 完成率；
- 完成后复测提升；
- 用户主观帮助度；
- 建议与诊断证据一致率；
- 重复、过载和不相关建议率。

## 11. MVP 边界

v0.1 只根据本次诊断生成下一动作。v0.2 再加入知识状态、时间和用户反馈。长期人生、职业或价值观建议不在本引擎范围。

