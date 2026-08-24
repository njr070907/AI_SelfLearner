# Current

## 当前里程碑

Sprint 1：用真实 Provider 验证 `evaluator-v0.1` 能否区分充分理解、部分理解、明确误区和证据不足。

## 当前状态

- 分支：`main`
- 任务：完成 DeepSeek `deepseek-v4-flash-vision-exp` 的完整 20 案例真实评估基线；接口适配、JSON 防护、失败诊断和 GitHub 协作者交接已完成，当前进入 Prompt v0.2 语义稳定性实验。
- 约束：默认 Fake；真实运行必须显式确认；每个案例零重试；任何成功结果仍需人工语义复核。

## 最近验证

- PR #3–#23 均已按 PR + CI 流程合并到 `main`；PR #23 的协作者交接包 CI 成功。
- 当前离线回归：82 tests、Ruff、format、Mypy、Secret Scan 全部通过；真实调用保持零重试。
- 真实运行 `deepseek-evaluator-v0.1-20260824T004542Z`：模型为指定实验模型，935/452 tokens，调用成功但自动检查 0/1；模型提取到 4 条证据，却额外记录了未列入覆盖点的缺口，导致 `fragile`/`re_explain`，与该 strong 黄金案例的 `solid`/`practice` 标准不符。
- 随后的两次受控调用 `20260824T005050Z`、`20260824T005448Z` 均为 `LLM_OUTPUT_INVALID`，0/0 tokens；未自动重试。
- 诊断后确认模型曾返回 JSON 但类型不稳定（`limitations` 字符串、置信度文字），已通过显式 JSON 类型指令修复。
- `deepseek-evaluator-v0.1-20260824T011349Z`：4/4 成功、自动检查 4/4 通过、3936/1233 tokens；四个场景分别得到 `solid/practice`、`fragile/re_explain`、`fragile/review`、`not_evident/re_explain`。
- 完整 20 案例真实调用均成功；多轮回归自动检查在 17–19/20 之间波动，最新运行 `deepseek-evaluator-v0.1-20260824T015320Z` 为 20/20 结构成功、17/20 自动通过、25274/7049 tokens。
- 剩余失败均为语义置信度或 gap 边界的随机波动，未出现新的 API、JSON、Schema 或证据摘录故障。

## Resume Point

当前代码链路已解决。下一步是负责人逐条复核 20 条语义结果，并设计 Prompt v0.2 的稳定性实验；在新实验方案确定前不再重复完整付费回归。

GitHub 工作项：

- [Prompt v0.2 语义稳定性实验](https://github.com/njr070907/AI_SelfLearner/issues/24)
- [20 条黄金案例人工复核](https://github.com/njr070907/AI_SelfLearner/issues/25)
- [自动结果与人工结论校准报告](https://github.com/njr070907/AI_SelfLearner/issues/26)
