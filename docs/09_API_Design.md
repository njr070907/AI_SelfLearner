# API 设计

## 1. 范围

Streamlit MVP 可直接调用 Application Service；本文定义稳定的应用边界，并作为未来 FastAPI 的接口基线。REST 路径统一使用 `/api/v1`。

## 2. 设计原则

- 资源名使用名词；
- 写操作支持幂等键；
- 错误返回稳定 `code`，不让客户端解析异常文本；
- API 只返回验证后的结构化结果；
- 长模型调用可先同步实现，超过体验阈值后再引入任务状态。

## 3. 创建会话

### `POST /api/v1/sessions`

请求：

```json
{
  "concept": "梯度下降",
  "learning_goal": "理解模型训练",
  "learner_level": "beginner",
  "context": null
}
```

响应 `201`：

```json
{
  "session_id": "uuid",
  "concept": {"id": "uuid", "name": "梯度下降"},
  "status": "created",
  "created_at": "2026-08-23T00:00:00Z"
}
```

## 4. 生成费曼问题

### `POST /api/v1/sessions/{session_id}/question`

请求可为空。响应：

```json
{
  "question_id": "uuid",
  "question": "请用自己的话解释……",
  "difficulty": "introductory",
  "status": "questioned"
}
```

`coverage_points` 默认不暴露给普通 UI，可通过内部调试端点或开发模式查看。

## 5. 提交回答并诊断

### `POST /api/v1/sessions/{session_id}/explanations`

请求：

```json
{
  "question_id": "uuid",
  "answer_text": "梯度下降就是……",
  "answer_type": "main"
}
```

`answer_type` 可以是 `main` 或 `follow_up`。`main` 只能在会话第一次回答时提交；诊断成功后，前端可以在同一 `session_id` 下提交 `follow_up`，系统会递增 `sequence_no`，保存新的证据/决定/动作并重新计算当前状态。前端不需要知道数据库表名，也不能跳过 Application Service 直接访问 Provider 或 SQLite。

同步响应 `201`：

```json
{
  "explanation_id": "uuid",
  "diagnosis_id": "uuid",
  "session_status": "diagnosed",
  "diagnosis": {
    "summary": "……",
    "mastery_level": "fragile",
    "scores": {
      "correctness": 65,
      "mechanism_understanding": 35,
      "depth": 30,
      "transfer": null
    },
    "accurate_points": [],
    "missing_points": [],
    "misconceptions": [],
    "evidence": [],
    "follow_up_question": "……",
    "next_action": {"type": "relearn_mechanism", "instruction": "……"},
    "confidence": 0.78,
    "limitations": []
  }
}
```

服务应先保存回答与 pending diagnosis，再调用模型；失败时返回可恢复状态。应用层返回的 `SessionView` 包含 `answer_count` 和 `can_submit_follow_up`，`DiagnosisView` 包含 `diagnosis_id`、`answer_type` 和 `sequence_no`，供 Streamlit 或未来 API 客户端稳定消费。

## 6. 获取会话

### `GET /api/v1/sessions/{session_id}`

返回概念、问题、回答、最新诊断、状态、错误和时间线。默认不返回模型原始响应。

### `GET /api/v1/sessions?concept_id=&status=&cursor=&limit=`

按时间倒序分页；`limit` 默认 20，最大 100。

## 7. 获取知识状态

### `GET /api/v1/knowledge-states`

返回用户各概念的当前掌握等级、置信度、证据数、趋势、分数变化、开放薄弱项数量、反馈数量与更新时间。它是可重算投影，不替代事件历史。

### `GET /api/v1/knowledge-states/{concept_id}`

返回当前状态、历史可比记录和误区统计。状态还包含 `trend`（`improving`/`stable`/`declining`/`insufficient_data`）、`score_delta`、`wrong_item_count`、`open_wrong_item_count`、`feedback_count`、`feedback_inaccurate_count`、`review_attempt_count`、`review_success_count` 和最多 5 条重复误区摘要。样本不足时 `trend` 为 `insufficient_data`。

## 8. 诊断反馈

### `POST /api/v1/diagnoses/{diagnosis_id}/feedback`

```json
{
  "verdict": "partial",
  "note": "遗漏判断正确，但我理解梯度方向。"
}
```

反馈会保存为 `diagnosis_feedback` 记录和 `feedback_submitted` 事件，支持 `Idempotency-Key`；`accurate`、`partial`、`inaccurate` 均不会直接改写原诊断，`inaccurate` 可作为用户纠正事件参与长期状态统计。原始回答、证据和模型版本始终保留。

## 9. 重试

### `POST /api/v1/diagnoses/{diagnosis_id}/retry`

仅对失败诊断可用。请求携带 `Idempotency-Key`；同一 Key 不重复创建诊断。重试保留旧失败记录。

## 10. 导出与删除（P1）

- `GET /api/v1/users/me/export?format=json|markdown`
- `DELETE /api/v1/users/me/data`

删除属于高影响操作，应二次确认并明确范围；导出应包含原始数据、派生状态和版本信息。

## 10.1 错题本

### `GET /api/v1/wrong-items?status=open|snoozed|mastered`

返回可追溯的错题/薄弱项列表。每条记录包含原题、用户回答、错误类型、诊断证据、修正建议、来源会话和当前状态；默认优先返回 `open` 项。

### `GET /api/v1/wrong-items/{wrong_item_id}`

返回一条错题详情，不返回 Provider 原始响应。

### `POST /api/v1/wrong-items/{wrong_item_id}/status`

```json
{
  "status": "mastered"
}
```

状态变更保留 `wrong_item_status_updated` 事件，支持幂等键；标记为 `mastered` 不删除原题、回答或诊断证据，也不直接改写 Mastery Protocol 的历史决定。

## 10.2 复习与复测

### `GET /api/v1/reviews/due?at=<ISO-8601>`

返回到期的复习项目，默认按到期时间升序。初版调度间隔为可配置的 `1/3/7` 天；队列项目包含原错题、概念、题目、当前间隔、尝试次数和上次结果。

### `POST /api/v1/reviews/{review_item_id}/retest`

```json
{
  "answer_text": "我现在用新的情境解释……"
}
```

成功复测按确定性规则推进间隔：正确进入下一个间隔，部分正确回到 3 天，错误回到 1 天；Provider 失败或输出无效只保留失败事件，不偷偷改变到期时间。请求必须支持幂等键。

复测会保存 `retest_submitted` 和 `review_scheduled` 事件。复测结果是调度证据，不会绕过 Mastery Engine 直接把概念永久标记为掌握。

## 11. 错误格式

```json
{
  "error": {
    "code": "LLM_OUTPUT_INVALID",
    "message": "诊断结果格式无效，回答已保存，可重试。",
    "retryable": true,
    "request_id": "uuid",
    "details": {}
  }
}
```

常见错误码：`VALIDATION_ERROR`、`SESSION_NOT_FOUND`、`INVALID_SESSION_STATE`、`LLM_TIMEOUT`、`LLM_RATE_LIMITED`、`LLM_OUTPUT_INVALID`、`DATABASE_ERROR`、`CONFIGURATION_ERROR`。

## 12. 状态机

```text
created → questioned → answered → diagnosed
                   └→ diagnosis_failed → answered (retry)
```

服务端验证状态转换；客户端不能直接指定最终状态。

## 13. 安全

- 未来远程 API 必须鉴权并按用户隔离；
- 日志不记录完整答案或 Prompt；
- 限制输入长度和内容类型；
- 材料与用户回答是数据，不作为系统指令；
- 原始模型响应仅管理员/本地调试可见。
