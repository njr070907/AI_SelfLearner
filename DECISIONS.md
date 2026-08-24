# Decisions

## 2026-08-24 — 真实 Provider 使用结构化输出

- 使用 OpenAI Responses API 的 Pydantic 结构化输出，将返回值直接约束为 `ProviderObservation`。
- Provider 只提取证据；`DemoMasteryEngine` 和 `DemoLearningPolicy` 仍分别负责状态判断与下一步动作。
- 第一版只实现评估能力，不为尚未版本化的问题生成 Prompt 偷加隐式行为。

## 2026-08-24 — 付费调用默认关闭

- Fake 是默认运行模式。
- 真实模式需要显式 Provider、API Key、非 Fake 模型名和付费确认标志。
- 单案例零重试，首轮默认 1 条，避免网络波动造成隐性费用。

## 2026-08-24 — DeepSeek 使用 Chat Completions JSON Output

- `deepseek-v4-flash-vision-exp` 不再走 OpenAI Responses API。
- 使用 `https://api.deepseek.com` 的 OpenAI 兼容 Chat Completions 和 `response_format={"type":"json_object"}`。
- DeepSeek 返回的 JSON 先在本地解析，再通过 `ProviderObservation` 严格校验；结构不完整不得进入 Mastery Engine。

## 2026-08-24 — 真实评估失败时停止盲目重试

- 真实运行固定为单案例、零自动重试；成功结果也必须人工语义复核。
- 一次成功调用暴露了 Prompt v0.1 的范围误判：未列入 `coverage_points` 的高级理论不能自动成为 gap；适配器增加范围约束，但暂不冒充 Prompt v0.2。
- 连续两次后续调用返回 `LLM_OUTPUT_INVALID` 且 0/0 tokens。已经完成受限 JSON 恢复与离线验证后仍失败，因此停止更多付费调用，等待模型/账号/接口稳定性确认。

## 2026-08-24 — DeepSeek 类型约束与 4 场景基线

- 不放宽 `ProviderObservation` 的严格 Schema；将数组和数值类型直接写入 DeepSeek JSON 指令。
- 将失败诊断限制为字段路径和错误类型，不保存模型原文、学习者答案或密钥。
- 类型修复后 4 个场景自动检查全部通过；完整 20 条属于新增付费范围，需单独批准。
