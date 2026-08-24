# Blocked

## DeepSeek 真实评估复核

- 状态：阻塞。适配器、JSON 模式、`thinking=disabled`、范围约束和受限 JSON 对象恢复均已通过 PR 合并；真实输出仍不稳定。
- 证据：`deepseek-evaluator-v0.1-20260824T004542Z` 成功返回并完成本地 Schema 校验，但自动检查为 0/1（额外制造 coverage_points 之外的 gap，导致 `fragile`/`re_explain`）；随后 `20260824T005050Z` 和 `20260824T005448Z` 返回 `LLM_OUTPUT_INVALID`，均为 0/0 Token。
- 已尝试：错误的 Responses API 已改为 Chat Completions；启用 JSON Output；关闭思考；加入明确 JSON 指令；限制缺口范围；允许从包裹说明文字中提取一个 JSON 对象；所有离线测试和 CI 均通过。
- 解除条件：先通过模型/账号/接口配置检查确认该实验模型能稳定返回可解析 JSON，或由负责人决定下一种经过验证的调用策略；之后仍只运行 1 个案例并人工复核。
- 安全边界：Key 不写入仓库、日志或运行产物；不再盲目重复付费调用；每个案例零自动重试。
