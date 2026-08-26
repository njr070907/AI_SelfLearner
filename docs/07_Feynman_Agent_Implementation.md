# Feynman Agent 实现设计

## 1. 目标

Feynman Agent 通过“要求用户用自己的话解释”来判断知识是否真正被理解。它不是作文评分器，也不是标准答案匹配器。

## 2. 端到端流程

```text
concept + context + level
        ↓
Question Generator
        ↓
question + coverage_points
        ↓
User Explanation
        ↓
Evaluator
        ↓
Diagnosis Schema Validation
        ↓
Persist + Report + Optional Follow-up
```

## 3. 问题生成器

### 输入

```json
{
  "concept": "梯度下降",
  "learning_goal": "理解机器学习训练过程",
  "learner_level": "beginner",
  "reference_points": [],
  "language": "zh-CN"
}
```

### 输出

```json
{
  "concept": "梯度下降",
  "question": "假设你要向没学过机器学习的人解释：梯度下降如何知道参数应该往哪个方向改？",
  "coverage_points": [
    "目标函数与误差",
    "梯度代表局部变化方向",
    "沿负梯度更新参数",
    "学习率控制步长"
  ],
  "difficulty": "introductory",
  "question_type": "mechanism",
  "prompt_version": "question-v0.1"
}
```

### 生成规则

- 一个问题只聚焦一个概念；
- 优先问“为什么/如何运作”，而非复述定义；
- 可用情境或类比，但不能暗示完整答案；
- 覆盖点是评估参考，不直接展示给用户；
- 领域事实不确定时标记需要参考材料。

## 4. 诊断器输入

```json
{
  "concept": "梯度下降",
  "question": "……",
  "coverage_points": ["……"],
  "user_answer": "梯度下降就是不断让误差变小。",
  "reference_points": [],
  "prior_state": null
}
```

## 5. 诊断输出 Schema

```json
{
  "summary": "抓住了优化目标，但没有解释方向与参数更新机制。",
  "mastery_level": "fragile",
  "scores": {
    "correctness": 65,
    "mechanism_understanding": 35,
    "depth": 30,
    "transfer": null
  },
  "accurate_points": ["知道目标是降低误差"],
  "missing_points": ["梯度方向", "参数更新", "学习率"],
  "misconceptions": [],
  "uncertain_points": ["尚无法判断是否理解局部最优"],
  "evidence": [
    {
      "answer_excerpt": "不断让误差变小",
      "supports": "理解优化目标",
      "strength": "medium"
    }
  ],
  "follow_up_question": "如果只知道误差变大或变小，算法怎样决定每个参数具体往哪个方向移动？",
  "next_action": {
    "type": "relearn_mechanism",
    "instruction": "用一维函数图解释梯度方向和学习率，再重新回答。"
  },
  "confidence": 0.78,
  "limitations": ["回答较短，无法判断应用能力"],
  "prompt_version": "evaluator-v0.1"
}
```

## 6. 掌握等级

- `no_clue`：完全未掌握，没有足够证据表明理解，可能空答、循环描述或完全偏题；
- `fragile`：部分正确，但关键机制缺失或有明显误区；
- `developing`：核心机制基本正确，仍缺少边界、深度或迁移；
- `solid`：核心事实与机制正确，能说明原因/边界，且无重大误区。

等级由规则与结构化证据共同决定，不应只由总分映射。

## 7. 评估 Prompt v0.1

```text
你是一名严谨、保守的认知诊断专家。

任务：根据用户对指定知识点的解释，判断目前有哪些理解证据。
你不是作文评分器，不要因为术语多、语言流畅或篇幅长而高估理解。

请依次完成：
1. 找出用户明确说对的内容；
2. 检查是否解释了核心机制，而非只复述结果或定义；
3. 区分事实错误、错误认知、关键遗漏、含糊表达和证据不足；
4. 从用户原文选取最短必要片段作为证据；
5. 生成一个最能区分“真懂/似懂”的追问；
6. 给出一个最小、可执行的下一步学习动作；
7. 若无法判断，降低 confidence 并写明限制。

安全规则：
- 不评价人格、智力或动机；
- 不根据一次回答推断长期学习风格；
- 不引用用户没有说过的话；
- 不把缺失内容自动判为错误认知；
- 严格按给定 JSON Schema 输出。
```

## 8. 追问机制

追问只选择一个信息增益最高的问题：

- 若回答像背定义：问机制或因果；
- 若机制正确但抽象：问具体例子；
- 若存在可能误区：构造能暴露误区的反例；
- 若缺少边界：问何时不适用；
- 若证据充分：问迁移应用。

MVP 最多一轮追问，避免无限对话模糊实验结果。

## 9. 结构化输出处理

1. 优先使用供应商的结构化输出能力；
2. 用 Pydantic 校验范围、枚举和嵌套字段；
3. 解析失败可发起一次“仅修复格式”的重试；
4. 第二次失败后保存原始响应和错误，不生成伪诊断；
5. UI 显示可重试状态，用户回答仍保留。

## 10. Cognitive Update

每次诊断产生一条不可变证据。知识状态更新使用：

- 当前诊断的等级与分数；
- 诊断置信度；
- 是否经过追问；
- 用户对诊断的反馈；
- 与过去记录的可比性与新近性。

误区只有在模型明确指出“用户表达了一个错误命题”时记录；缺失点不能直接成为误区。

## 11. 测试重点

- 表达简短但理解正确；
- 长篇复述但缺少机制；
- 部分正确且有一个关键误区；
- 完全错误、偏题或空回答；
- 标准答案之外但合理的解释；
- 无参考材料的专业概念；
- Prompt 注入式回答；
- 模型返回无效 JSON、缺字段或越界分数。

## 12. MVP 完成定义

- 输入任意常见概念可生成可回答的问题；
- 对固定强/弱/误区答案给出稳定、可解释区分；
- 诊断带证据、置信度和版本；
- 失败可恢复且不丢回答；
- 一次会话完整保存并可在历史页重放。
