# Current

## 当前里程碑

Sprint 1：用真实 Provider 验证 `evaluator-v0.1` 能否区分充分理解、部分理解、明确误区和证据不足；并行把学习工作区扩展成完整自学 MVP。

## MVP 总进度

**约 53% / 100%** · **阶段 5「真实 AI 发布边界与评测产品化」后端安全边界已完成**；阶段 1–4 的用户页面和真实语义验收仍待完成。预计还需 **12–20 个有效工作日**（前后端并行、每天 4–6 小时约 4–6 周）。

完整阶段权重和计算方式见 [`docs/roadmap/MVP_PROGRESS.md`](docs/roadmap/MVP_PROGRESS.md)。这是按最终用户可正常使用的功能验收权重，不按代码量或已经经过的时间计算；当前 53% 不代表日历时间已经过去 53%。

## 当前状态

- 分支：`main`
- 任务：DeepSeek `deepseek-v4-flash-vision-exp` 的完整 20 案例真实评估基线已完成；接口适配、JSON 防护、失败诊断、GitHub 协作者交接、UI v1、教学闭环后端、错题本后端、复习调度后端、反馈/长期状态后端和 Provider Factory 已完成。完整自学 MVP 计划已写入 `docs/roadmap/FULL_SELF_STUDY_MVP_PLAN.md`，GitHub Issues #31–#39 已建立；当前由前端接入 #33/#35/#37，随后完成真实语义验收并进入 #39 全链路集成与 7 天试用。
- 约束：默认 Fake；真实运行必须显式确认；每个案例零重试；任何成功结果仍需人工语义复核。

## 最近验证

- PR #3–#29 均已按 PR + CI 流程合并到 `main`；PR #28 建立 Liquid Glass 学习工作区，PR #29 完成动效、光效、导航指示器和下拉定位修复；两次合并后的 CI 均成功。
- 当前离线回归：139 tests、Ruff、format、Mypy 全部通过；真实调用保持零重试。#38、#45 已合并；阶段 4 后端能力和阶段 5 Provider 安全边界已计入当前进度。
- 真实运行 `deepseek-evaluator-v0.1-20260824T004542Z`：模型为指定实验模型，935/452 tokens，调用成功但自动检查 0/1；模型提取到 4 条证据，却额外记录了未列入覆盖点的缺口，导致 `fragile`/`re_explain`，与该 strong 黄金案例的 `solid`/`practice` 标准不符。
- 随后的两次受控调用 `20260824T005050Z`、`20260824T005448Z` 均为 `LLM_OUTPUT_INVALID`，0/0 tokens；未自动重试。
- 诊断后确认模型曾返回 JSON 但类型不稳定（`limitations` 字符串、置信度文字），已通过显式 JSON 类型指令修复。
- `deepseek-evaluator-v0.1-20260824T011349Z`：4/4 成功、自动检查 4/4 通过、3936/1233 tokens；四个场景分别得到 `solid/practice`、`fragile/re_explain`、`fragile/review`、`not_evident/re_explain`。
- 完整 20 案例真实调用均成功；多轮回归自动检查在 17–19/20 之间波动，最新运行 `deepseek-evaluator-v0.1-20260824T015320Z` 为 20/20 结构成功、17/20 自动通过、25274/7049 tokens。
- 剩余失败均为语义置信度或 gap 边界的随机波动，未出现新的 API、JSON、Schema 或证据摘录故障。

## Resume Point

当前代码链路、UI v1、#32 教学闭环后端、#34 错题本后端、#36 复习调度后端、#38 长期状态后端和 #45 Provider Factory 已完成；Prompt v0.2 候选版本已经可以通过 `--prompt-version v0.2` 做零成本 dry-run。完整自学 MVP 的下一步是由前端合作者接入 #33/#35/#37，再完成真实语义验收和 #39 全链路集成、7 天试用。未合并代码不计入进度。

GitHub 工作项：

- [Prompt v0.2 语义稳定性实验](https://github.com/njr070907/AI_SelfLearner/issues/24)
- [20 条黄金案例人工复核](https://github.com/njr070907/AI_SelfLearner/issues/25)
- [自动结果与人工结论校准报告](https://github.com/njr070907/AI_SelfLearner/issues/26)
- [完整自学 MVP 计划](https://github.com/njr070907/AI_SelfLearner/blob/main/docs/roadmap/FULL_SELF_STUDY_MVP_PLAN.md)
- [MVP 进度面板](https://github.com/njr070907/AI_SelfLearner/blob/main/docs/roadmap/MVP_PROGRESS.md)
- [完整自学 MVP 工作项 #31–#39](https://github.com/njr070907/AI_SelfLearner/issues?q=is%3Aissue+label%3Aenhancement)
