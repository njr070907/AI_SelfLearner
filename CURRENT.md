# Current

## 当前里程碑

Sprint 1：用真实 Provider 验证 `evaluator-v0.1` 能否区分充分理解、部分理解、明确误区和证据不足。

## 当前状态

- 基线分支：`main`
- 任务：OpenAI Responses API 评估适配器、付费调用安全门和离线测试已通过 PR #4 合并。
- 约束：默认 Fake；真实运行必须显式确认；每个案例零重试；任何成功结果仍需人工语义复核。

## 最近验证

- PR #3 已于 2026-08-24 合并到 `main`。
- PR #3 合并前 CI 全部通过：55 tests、lint、format、migration、启动、Secret Scan、Fake 闭环。
- 合并后 `main` CI 已成功。
- 当前分支 69 tests、lint、format、mypy、87% coverage、Secret Scan、migration、Fake 闭环、Streamlit 启动与依赖审计通过。
- PR #4 和状态更新 PR #5 均已合并；两次合并后的 `main` CI 均已成功。

## Resume Point

实际发起模型调用前，由用户在本机提供 OpenAI API Key、指定可用的精确模型，并明确授权最多 1 个案例的真实费用；随后运行并人工复核首条结果。
