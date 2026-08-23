# 系统架构与数据流

## 1. MVP 架构决策

MVP 是单进程模块化应用：Streamlit 承担界面与应用入口，领域服务处理学习流程，Repository 隔离 SQLite，Provider 隔离外部 LLM。暂不拆分前后端和微服务。

```text
[User]
   |
[Streamlit UI]
   |
[Application Service] ---- [Request/Schema Validation]
   |             |
   |             +---- [Prompt Registry]
   |             +---- [LLM Provider] ---- [External LLM]
   |
[Repository Interface]
   |
[SQLite + Migrations]

Cross-cutting: auth boundary (future), redacted logs, metrics, trace/request ID
```

## 2. 模块职责

| 模块 | 负责 | 不负责 |
|---|---|---|
| UI | 输入、展示、会话状态、可恢复错误 | Prompt 拼装、SQL、模型解析 |
| Domain/Application | 流程编排、业务规则、幂等性 | 厂商 SDK、页面组件 |
| Agent/Prompt | 问题与诊断任务定义 | 数据库写入、用户权限 |
| Provider | 模型调用、超时、重试、原始响应封装 | 业务结论 |
| Schema | 输入输出验证与版本 | 自动“修正”错误语义 |
| Repository | 事务、查询、数据映射 | 业务评分 |
| Observability | 脱敏事件、指标、错误关联 | 保存完整学习内容 |

## 3. 核心时序

```text
User -> UI: 创建主题
UI -> Service: start_session(request_id, topic)
Service -> Provider: generate_questions(prompt_version)
Provider -> Service: response + model metadata
Service -> Schema: validate
Service -> Repository: save session/questions/version
Service -> UI: questions
User -> UI: submit answer
UI -> Service: evaluate(session_id, answer, request_id)
Service -> Provider: evaluate with bounded context
Provider -> Schema: structured diagnosis
Schema -> Service: validated result
Service -> Repository: atomic save answer + diagnosis + versions
Service -> UI: diagnosis
```

任何一步失败都不得保存“部分成功”的诊断。回答可先本地暂存；诊断写入与版本元数据在一个事务内完成。

## 4. 数据边界

- 外发给模型：完成当前任务所需的最小主题、回答和经选择的历史证据。
- 不外发：密钥、内部日志、其他用户内容、无关画像、删除标记数据。
- 数据库存储：用户输入、生成问题、诊断、反馈、版本、时间和审计事件。
- 日志存储：ID、耗时、状态、错误类别、token/成本估算；默认不存正文。

## 5. 稳定接口

推荐领域接口：

```python
start_session(topic, goal, request_id) -> Session
generate_questions(session_id) -> QuestionSet
evaluate_answer(session_id, answer, request_id) -> Diagnosis
submit_feedback(diagnosis_id, verdict, note) -> Feedback
export_user_data(user_id) -> ExportArtifact
delete_user_data(user_id) -> DeletionReceipt
```

Provider 接口至少返回 `content`、`provider`、`model`、`model_revision`（若可得）、`prompt_version`、`latency_ms`、`usage`、`finish_reason` 和 `request_id`。

## 6. 失败策略

- 超时：最多重试 2 次，指数退避；用户主动重试使用相同幂等键。
- 限流：显示可理解提示，不切换到未经评估的模型。
- Schema 错误：允许一次受控修复；仍失败则记录失败，不展示伪造诊断。
- 数据库失败：事务回滚；保留 UI 中尚未提交的回答。
- 未知错误：生成错误 ID，日志脱敏，向用户提供重试或导出草稿。

## 7. 演进触发器

只有出现以下证据才升级架构：

- 需要独立 API 客户端时，引入 FastAPI。
- SQLite 锁竞争或多用户并发成为实测瓶颈时，迁移 PostgreSQL。
- 检索质量测试证明关键词/结构化检索不足时，引入向量检索。
- 单进程部署无法满足已批准 SLO 时，拆分后台任务。

所有演进必须新增 ADR、迁移与回滚方案。

