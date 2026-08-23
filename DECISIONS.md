# Decisions

## 2026-08-24 — 真实 Provider 使用结构化输出

- 使用 OpenAI Responses API 的 Pydantic 结构化输出，将返回值直接约束为 `ProviderObservation`。
- Provider 只提取证据；`DemoMasteryEngine` 和 `DemoLearningPolicy` 仍分别负责状态判断与下一步动作。
- 第一版只实现评估能力，不为尚未版本化的问题生成 Prompt 偷加隐式行为。

## 2026-08-24 — 付费调用默认关闭

- Fake 是默认运行模式。
- 真实模式需要显式 Provider、API Key、非 Fake 模型名和付费确认标志。
- 单案例零重试，首轮默认 1 条，避免网络波动造成隐性费用。
