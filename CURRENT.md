# Current

## 当前里程碑

Sprint 1：用真实 Provider 验证 `evaluator-v0.1` 能否区分充分理解、部分理解、明确误区和证据不足。

## 当前状态

- 分支：`main`
- 任务：完成 DeepSeek `deepseek-v4-flash-vision-exp` 的首条真实评估复核；接口适配、JSON 防护和协作 PR 已完成，但真实输出稳定性仍阻塞语义验收。
- 约束：默认 Fake；真实运行必须显式确认；每个案例零重试；任何成功结果仍需人工语义复核。

## 最近验证

- PR #3–#11 均已按 PR + CI 流程合并到 `main`；PR #9、#10、#11 及各自合并后的 `main` CI 均成功。
- 当前离线回归：79 tests、Ruff、format、Mypy 全部通过；真实调用仍保持单案例、零重试。
- 真实运行 `deepseek-evaluator-v0.1-20260824T004542Z`：模型为指定实验模型，935/452 tokens，调用成功但自动检查 0/1；模型提取到 4 条证据，却额外记录了未列入覆盖点的缺口，导致 `fragile`/`re_explain`，与该 strong 黄金案例的 `solid`/`practice` 标准不符。
- 随后的两次受控调用 `20260824T005050Z`、`20260824T005448Z` 均为 `LLM_OUTPUT_INVALID`，0/0 tokens；未自动重试。

## Resume Point

停止新增付费调用；下一次恢复时，先确认 DeepSeek 该实验模型的稳定 JSON 输出或选择经过验证的请求配置，再继续 1 条案例，不能直接扩展到 4/20 条。
