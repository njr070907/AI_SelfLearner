# Current

## 当前里程碑

Sprint 1：用真实 Provider 验证 `evaluator-v0.1` 能否区分充分理解、部分理解、明确误区和证据不足。

## 当前状态

- 分支：`main`
- 任务：完成 DeepSeek `deepseek-v4-flash-vision-exp` 的 4 场景真实评估基线；接口适配、JSON 防护、失败诊断和协作 PR 已完成，当前等待负责人完成逐条人工语义复核。
- 约束：默认 Fake；真实运行必须显式确认；每个案例零重试；任何成功结果仍需人工语义复核。

## 最近验证

- PR #3–#15 均已按 PR + CI 流程合并到 `main`；最近 PR #13、#14、#15 及各自合并后的 `main` CI 均成功。
- 当前离线回归：81 tests、Ruff、format、Mypy 全部通过；真实调用保持零重试。
- 真实运行 `deepseek-evaluator-v0.1-20260824T004542Z`：模型为指定实验模型，935/452 tokens，调用成功但自动检查 0/1；模型提取到 4 条证据，却额外记录了未列入覆盖点的缺口，导致 `fragile`/`re_explain`，与该 strong 黄金案例的 `solid`/`practice` 标准不符。
- 随后的两次受控调用 `20260824T005050Z`、`20260824T005448Z` 均为 `LLM_OUTPUT_INVALID`，0/0 tokens；未自动重试。
- 诊断后确认模型曾返回 JSON 但类型不稳定（`limitations` 字符串、置信度文字），已通过显式 JSON 类型指令修复。
- `deepseek-evaluator-v0.1-20260824T011349Z`：4/4 成功、自动检查 4/4 通过、3936/1233 tokens；四个场景分别得到 `solid/practice`、`fragile/re_explain`、`fragile/review`、`not_evident/re_explain`。

## Resume Point

当前代码问题已解决。下一步是负责人逐条确认 4 个真实案例的语义结果；如需扩展完整 20 条，必须再次明确批准相应付费调用。
