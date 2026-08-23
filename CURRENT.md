# Current

## 当前里程碑

Sprint 1：用真实 Provider 验证 `evaluator-v0.1` 能否区分充分理解、部分理解、明确误区和证据不足。

## 当前状态

- 分支：`feature/sprint1-openai-provider`
- 任务：OpenAI Responses API 评估适配器、付费调用安全门和离线测试已实现，等待提交 PR。
- 约束：默认 Fake；真实运行必须显式确认；每个案例零重试；任何成功结果仍需人工语义复核。

## 最近验证

- PR #3 已于 2026-08-24 合并到 `main`。
- PR #3 合并前 CI 全部通过：55 tests、lint、format、migration、启动、Secret Scan、Fake 闭环。
- 合并后 `main` CI 已成功。
- 当前分支 69 tests、lint、format、mypy、87% coverage、Secret Scan、migration、Fake 闭环、Streamlit 启动与依赖审计通过。

## Resume Point

提交并创建 OpenAI 适配器 PR；CI 通过后可合并。实际发起模型调用仍需用户提供 API Key 并明确授权真实费用。
