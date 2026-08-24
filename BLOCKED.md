# Blocked

## DeepSeek 真实首条复核

- 状态：第一次调用已执行但被供应商拒绝；修复后的 Chat Completions 适配器已通过离线测试，尚未重新调用。
- 原因：旧实现把 DeepSeek 模型发送到了 OpenAI Responses API；结果记录为 `LLM_REQUEST_REJECTED`，Token 为 0。
- 解除条件：使用 `--provider deepseek` 重新运行固定模型 `deepseek-v4-flash-vision-exp`，并继续遵守最多 1 个案例、零自动重试。
- 安全边界：Key 不写入仓库、日志或运行产物；首次最多运行 1 个案例；零自动重试。
