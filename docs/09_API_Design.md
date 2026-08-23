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

服务应先保存回答与 pending diagnosis，再调用模型；失败时返回可恢复状态。

## 6. 获取会话

### `GET /api/v1/sessions/{session_id}`

返回概念、问题、回答、最新诊断、状态、错误和时间线。默认不返回模型原始响应。

### `GET /api/v1/sessions?concept_id=&status=&cursor=&limit=`

按时间倒序分页；`limit` 默认 20，最大 100。

## 7. 获取知识状态

### `GET /api/v1/knowledge-states`

返回用户各概念的掌握等级、置信度、证据数与更新时间。

### `GET /api/v1/knowledge-states/{concept_id}`

返回当前状态、历史可比记录和误区统计。样本不足时 `trend` 为 `insufficient_data`。

## 8. 诊断反馈

### `POST /api/v1/diagnoses/{diagnosis_id}/feedback`

```json
{
  "rating": "partial",
  "comment": "遗漏判断正确，但我理解梯度方向。"
}
```

反馈用于模型评估和状态置信度更新，不能直接改写原诊断。

## 9. 重试

### `POST /api/v1/diagnoses/{diagnosis_id}/retry`

仅对失败诊断可用。请求携带 `Idempotency-Key`；同一 Key 不重复创建诊断。重试保留旧失败记录。

## 10. 导出与删除（P1）

- `GET /api/v1/users/me/export?format=json|markdown`
- `DELETE /api/v1/users/me/data`

删除属于高影响操作，应二次确认并明确范围；导出应包含原始数据、派生状态和版本信息。

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

