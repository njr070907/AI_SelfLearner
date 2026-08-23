# AI Agent 架构

## 1. 设计目标

用最少的智能模块完成可观察、可测试、可替换的学习诊断流程。文档描述长期逻辑架构；MVP 代码可在单进程内实现，不能为了“Agent 感”拆成分布式系统。

## 2. 逻辑架构

```text
                       Mentor / Orchestrator
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
 Knowledge Agent       Feynman Agent        Growth Recommender
        │                      │                      │
        └─────────────── Cognitive Engine ────────────┘
                               │
                     Memory + Evidence Store
```

MVP 只实现 Feynman Agent 的问题生成与诊断，以及最基础的记录保存。其余模块以清晰接口预留，不创建空壳服务。

## 3. Knowledge Agent

### 职责

- 把材料或主题转换为核心概念与前置依赖；
- 提供诊断所需的参考要点；
- 标记材料来源、可引用片段与不确定项。

### 输入与输出

输入：主题、可选材料片段、目标和当前水平。  
输出：`knowledge_nodes`、`prerequisites`、`reference_points`、`source_refs`。

### 边界

- 不判断用户掌握程度；
- 不凭空扩展材料内容；
- MVP 主题模式可直接由问题生成器生成覆盖点，不必独立运行。

## 4. Feynman Agent

### 子能力 A：Question Generator

- 生成要求解释“是什么、为什么、如何运作、何时失效”的开放问题；
- 根据难度选择直觉、机制或迁移层级；
- 避免在问题中提供答案；
- 返回预期覆盖点，供评估阶段使用。

### 子能力 B：Evaluator / Diagnostician

- 识别用户说对了什么；
- 判断核心机制是否出现；
- 区分错误认知、遗漏、模糊和无证据；
- 生成一个高信息增益追问；
- 以证据与置信度输出诊断。

### 评估优先级

```text
事实正确性  >  核心机制  >  错误认知  >  深度/迁移  >  表达结构
```

表达能力只能作为“是否能清楚说明”的辅助信号，不能代替理解判断。

## 5. Cognitive Engine

负责把一次诊断转换为保守的状态更新：

- 更新某概念的掌握估计；
- 记录误区及其证据；
- 检测跨会话重复模式；
- 维护置信度、支持证据与反证；
- 接收用户纠正。

只有单次证据时，应写成事件或候选模式，不能写成稳定画像。

## 6. Mentor Agent

负责交互策略与长期语气，而不是替代其他模块判断：

- 用用户能理解的方式呈现诊断；
- 解释建议依据；
- 在多个候选行动中给出最小下一步；
- 尊重用户目标与选择；
- 不越界进行心理、人格或人生定论。

MVP 中它可以是报告格式化层，而不是独立模型调用。

## 7. Growth Recommendation Engine

从以下候选行动中排序：

- 补一个前置概念；
- 换一种解释（类比、图示、公式、案例）；
- 回答一个追问；
- 完成一个迁移应用；
- 安排间隔复习；
- 继续下一个概念。

推荐必须引用当前诊断与历史状态，并限制为 1 个主要行动、最多 2 个备选行动。

## 8. Orchestration

建议在应用服务层以确定性代码编排：

```python
question = question_generator.generate(session_context)
diagnosis = evaluator.evaluate(question, user_answer, references)
validated = diagnosis_schema.validate(diagnosis)
record = repository.save(session, question, answer, validated)
state = cognitive_engine.update(record)
recommendation = recommender.choose(state, validated)
```

不要让一个自由运行 Agent 决定是否保存、删除或修改用户数据。

## 9. 共享上下文

每次模型调用只包含完成任务所需的最小上下文：

- 当前概念与用户目标；
- 当前问题和覆盖点；
- 用户原始回答；
- 必要参考材料；
- 少量相关历史摘要；
- 输出 Schema 与安全规则。

长期历史先检索、再注入，避免把所有会话塞入上下文。

## 10. 可靠性设计

- 所有输出经过 Schema 校验；
- 保存原始响应用于调试，但不直接驱动 UI；
- 解析失败仅重试一次，随后返回可恢复错误；
- 每条记录保存模型、Prompt、Schema 和评估版本；
- 关键判断包含用户回答证据；
- 可以用固定案例离线比较新旧版本；
- 模型不可用时保留用户输入，允许稍后重试。

## 11. 未来多 Agent 的进入条件

只有当材料处理、诊断、推荐在规模或模型要求上出现明确独立需求时才拆分。进入多 Agent 前必须证明：

- 单一调用无法稳定完成任务；
- 子任务有独立评估集；
- 额外调用的成本和延迟可接受；
- 编排失败有清晰恢复策略。

