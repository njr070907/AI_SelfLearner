# Feynman Agent MVP Code Spec

## 1. 范围

定义第一版代码必须实现的最小闭环、文件职责、函数输入输出、状态与测试。本文优先级高于未来架构设想。

## 2. 核心闭环

```text
用户输入知识点
    ↓
AI 生成费曼问题
    ↓
用户解释
    ↓
AI 诊断
    ↓
保存记录
    ↓
展示报告与历史
```

## 3. 必需文件

```text
app.py
src/
├─ agents/
│  ├─ question_generator.py
│  └─ evaluator.py
├─ application/
│  ├─ session_service.py
│  └─ diagnosis_service.py
├─ domain/
│  ├─ models.py
│  ├─ schemas.py
│  └─ errors.py
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
tests/
```

## 4. 领域模型

### LearningSession

```python
id: str
user_id: str
concept_id: str
status: SessionStatus
learning_goal: str | None
learner_level: str | None
started_at: datetime
completed_at: datetime | None
```

### FeynmanQuestion

```python
id: str
session_id: str
concept: str
question_text: str
coverage_points: list[str]
difficulty: str
question_type: str
prompt_version: str
model_name: str
```

### UserExplanation

```python
id: str
session_id: str
question_id: str
answer_text: str
answer_type: Literal["main", "follow_up"]
sequence_no: int
created_at: datetime
```

### Diagnosis

字段遵循 `07_Feynman_Agent_Implementation.md`；使用 Pydantic 严格校验分数、枚举、证据和下一步。

## 5. 函数规格

### `normalize_concept(value: str) -> str`

去除首尾空白并标准化重复空格；不擅自翻译或改写。无效长度抛 `ValidationError`。

### `QuestionGenerator.generate(request) -> FeynmanQuestion`

只负责 Prompt 与结构化输出；不写数据库，不操作 UI。

### `Evaluator.evaluate(request) -> DiagnosisResult`

接收问题、覆盖点、用户原文和可选参考；返回诊断与模型运行元数据。

### `SessionService.start_session(command) -> SessionView`

创建/复用概念、创建会话、生成并保存问题。模型失败时会话状态为 `question_failed`，可重试。

### `DiagnosisService.submit_answer(command) -> DiagnosisView`

必须按顺序：验证 → 保存回答 → 保存 pending 诊断 → 外部调用 → 校验 → 保存成功结果 → 更新会话。外部调用不在数据库事务中。

### `DiagnosisService.retry(diagnosis_id) -> DiagnosisView`

仅重试失败记录；使用同一回答，创建新的运行/诊断尝试并保留旧失败。

## 6. 状态机

```text
created
  ├─ question success → questioned
  └─ failure → question_failed → created (retry)

questioned
  └─ save answer → answered

answered
  ├─ diagnosis success → diagnosed
  └─ failure → diagnosis_failed → answered (retry)
```

非法转换抛 `InvalidSessionState`，不静默修正。

## 7. 数据一致性

- 每个 P0 会话一个主问题；
- 用户回答不可因模型失败回滚；
- 只有 succeeded diagnosis 更新知识状态；
- `result_json` 与可查询分数字段一致；
- 所有记录有 UTC 时间；
- 重复提交通过 UI 禁用、幂等键或状态检查防护。

## 8. LLM Client

```python
class LLMClient(Protocol):
    def generate_structured(
        self,
        messages: list[Message],
        response_model: type[T],
        config: LLMCallConfig,
    ) -> LLMCallResult[T]: ...
```

实现 `FakeLLMClient` 与一个真实 Adapter。业务层不知道供应商 SDK 类型。

## 9. UI 行为

- session id 存于 Streamlit session state；
- 页面刷新时可从数据库恢复；
- 提交期间按钮禁用；
- 错误显示数据是否保存和重试操作；
- 不在 UI 直接访问 SQL 或调用 LLM；
- History 点击记录可重建 Diagnosis View。

## 10. 配置与日志

启动时校验环境变量。日志使用 request/session/diagnosis id 关联，默认不打印完整用户回答、Prompt、原始模型输出或 Key。

## 11. 必须测试

- 概念与回答边界；
- Question/Diagnosis Schema；
- 成功闭环；
- 超时、限流、无效 JSON；
- 回答在失败后仍保存；
- 重试和重复提交；
- 应用重启后历史；
- 数据库约束与级联；
- Prompt 注入内容不改变任务；
- 测试不调用真实 API。

## 12. MVP 不做

- 复杂用户系统；
- 多 Agent；
- 完整知识图谱；
- PDF/RAG；
- 商业功能；
- React/Electron/FastAPI；
- 长期人格模型。

## 13. 完成定义

在干净环境：安装 → 配置 → 初始化 → 启动；用户可完成一次真实诊断；失败可恢复；记录可重开；测试通过；README 与实际一致；没有范围外依赖和功能。

