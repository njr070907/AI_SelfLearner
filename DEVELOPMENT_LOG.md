# Development Log

## 2026-08-24

- 合并 PR #3：Prompt v0.1 评估 Runner 与 Mastery Protocol v0.2 基线。
- 创建 `feature/sprint1-openai-provider`。
- 依据 OpenAI 官方结构化输出文档，开始实现 Responses API + Pydantic 适配器。
- 完成真实评测 CLI 的三重安全门、默认单案例、零重试和输出 token 上限。
- 全离线 Mock 覆盖成功与主要失败路径；完整回归为 69 tests、87% coverage，所有项目检查通过。
- PR #3 合并后的 `main` CI 已成功。
- PR #4 CI 成功并已 squash 合并到 `main`；真实付费评测尚未启动。
- 状态更新 PR #5 及合并后的 `main` CI 成功；修正操作 Backlog 指向完整需求文件的链接。
- 首条真实调用使用了错误的 Responses API，结果为 `LLM_REQUEST_REJECTED`、Token 0；没有自动重试。
- 依据 DeepSeek 官方 JSON Output/兼容接口说明，开始改为 Chat Completions 适配器，固定 `deepseek-v4-flash-vision-exp`。
- DeepSeek 适配器离线回归完成：77 tests、86% coverage、lint、format、mypy、migration、启动、Secret Scan 和依赖审计通过。
- 额度状态：`UNKNOWN`，环境没有提供可靠 remaining quota 信息。
