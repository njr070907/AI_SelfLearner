# Feynman Agent 代码架构

## 1. 目标

把问题生成、诊断、状态更新和界面分开，使每部分可独立测试和替换，同时保持 MVP 简单。

## 2. 模块结构

```text
src/
├─ agents/
│  ├─ question_generator.py
│  ├─ evaluator.py
│  └─ models.py
├─ application/
│  ├─ session_service.py
│  ├─ diagnosis_service.py
│  └─ history_service.py
├─ domain/
│  ├─ entities.py
│  ├─ schemas.py
│  ├─ errors.py
│  └─ cognitive_update.py
├─ infrastructure/
│  ├─ llm_client.py
│  ├─ database.py
│  └─ repositories.py
├─ prompts/
│  ├─ question_v0_1.md
│  └─ evaluator_v0_1.md
└─ ui/
   ├─ home.py
   ├─ session.py
   ├─ diagnosis.py
   └─ history.py
```

## 3. 核心接口

### QuestionGenerator

```python
class QuestionGenerator(Protocol):
    def generate(self, request: QuestionRequest) -> FeynmanQuestion: ...
```

### Evaluator

```python
class Evaluator(Protocol):
    def evaluate(self, request: EvaluationRequest) -> Diagnosis: ...
```

### SessionRepository

```python
class SessionRepository(Protocol):
    def create(self, session: LearningSession) -> None: ...
    def save_question(self, question: FeynmanQuestion) -> None: ...
    def save_explanation(self, explanation: UserExplanation) -> None: ...
    def save_diagnosis(self, diagnosis: Diagnosis) -> None: ...
    def get(self, session_id: str) -> LearningSessionView: ...
```

## 4. 服务职责

### SessionService

验证输入、规范化概念、创建会话、调用 QuestionGenerator、保存问题并返回 View Model。

### DiagnosisService

1. 验证会话状态；
2. 保存用户回答；
3. 创建 pending diagnosis；
4. 调用 Evaluator；
5. 校验结果；
6. 事务性保存并完成会话；
7. 调用状态更新；
8. 失败时保留回答并记录可重试错误。

### HistoryService

查询会话列表、同概念历史和简单趋势，不调用 LLM。

## 5. 领域对象

- 倾向不可变 dataclass/Pydantic model；
- 时间统一 UTC；
- 枚举表示状态和等级；
- AI 原始响应不进入 `Diagnosis` 领域对象，保存在运行元数据；
- UI 文案由 View Model 生成，不改变领域事实。

## 6. 错误模型

```text
ValidationError
ConfigurationError
InvalidSessionState
LLMTimeout
LLMRateLimited
LLMOutputInvalid
PersistenceError
```

基础设施异常在边界处转换，不让 UI 依赖供应商异常类型。

## 7. 依赖方向

```text
UI → Application → Domain
Infrastructure → Domain interfaces
Agents → LLM abstraction + Domain schemas
```

Domain 不导入 Streamlit、SQLite 或供应商 SDK。

## 8. 事务边界

- 创建会话与问题保存可作为一个用例；
- 回答先独立持久化，再进行外部模型调用；
- 模型成功后在短事务中保存诊断与状态；
- 不在数据库事务内等待网络调用。

## 9. 测试映射

| 模块 | 测试 |
|---|---|
| schemas | 边界、枚举、缺字段 |
| question_generator | Prompt 渲染、结构解析 |
| evaluator | 强/弱/误区 fixture |
| diagnosis_service | 成功、超时、无效 JSON、重试 |
| repository | CRUD、约束、级联 |
| cognitive_update | 单次影响、反证、失败不更新 |
| UI | 核心流程与错误消息 |

## 10. 扩展边界

未来可增加 `KnowledgeProvider`、`MemoryRetriever`、`RecommendationPolicy`，但只有真实功能进入时创建。禁止提前建立未使用的 Agent 基类和插件框架。

