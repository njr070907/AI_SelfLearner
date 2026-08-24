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
- 第二次 DeepSeek 尝试到达 Chat Completions 但返回空/不可用内容，Token 0；增加 `thinking=disabled` 的 JSON 模式后再验证。
- 第三次尝试返回非 JSON 内容，Token 0；增加明确的小写 `json` 指令和仅限外层代码围栏的解析，再验证。
- PR #7–#11 均已 squash 合并；每个 PR 的 CI 与合并后的 `main` CI 均成功。
- `deepseek-evaluator-v0.1-20260824T004542Z` 使用 `deepseek-v4-flash-vision-exp` 成功返回 935/452 tokens；4 条证据均有原文依据，但模型把未列入 coverage_points 的深入 ε-δ 解释记为 gap，确定性引擎因此得到 `fragile`/`re_explain`，自动检查 0/1。
- 为修复该误判，加入 coverage scope guard；为处理协议外包裹文字，加入单 JSON 对象恢复；PR #10/#11 及合并后 CI 均通过。
- 两次修复后的真实调用 `deepseek-evaluator-v0.1-20260824T005050Z`、`deepseek-evaluator-v0.1-20260824T005448Z` 仍为 `LLM_OUTPUT_INVALID`、0/0 tokens；按安全边界停止付费重试。
- 完整离线回归：79 tests、Ruff、format、Mypy 全部通过。
- 额度状态：`UNKNOWN`，环境没有提供可靠 remaining quota 信息。
