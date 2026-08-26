# Current

## 当前里程碑

Sprint 1：用真实 Provider 验证 `evaluator-v0.1` 能否区分充分理解、部分理解、明确误区和证据不足；并行把学习工作区扩展成完整自学 MVP。

## MVP 总进度

**约 66% / 100%** · **阶段 1「自学教学闭环」已成为可操作用户路径**；错题、复习和长期状态页面正在功能分支完成集成，真实语义验收与连续试用仍待完成。预计还需 **10–18 个有效工作日**，其中真实 7 天试用必须按自然日发生，不能由自动化测试替代。

完整阶段权重和计算方式见 [`docs/roadmap/MVP_PROGRESS.md`](docs/roadmap/MVP_PROGRESS.md)。这是按最终用户可正常使用的功能验收权重，不按代码量或已经经过的时间计算；当前 56% 不代表日历时间已经过去 56%。

## 当前状态

- 分支：`feat/35-37-39-self-study-loop`（以 `main` 的 PR #58 / Issue #33 为基线）
- 任务：学习教学页面 #33 已合并；本分支已完成 #35 错题本、#37 复习复测和 #39 的 Fake 全链路集成候选，PR #59 正在等待人工审核。真实 DeepSeek 语义验收和实际 7 个自然日试用仍未完成。
- 约束：默认 Fake；真实运行必须显式确认；每个案例零重试；任何成功结果仍需人工语义复核。

## 最近验证

- PR #3–#29 均已按 PR + CI 流程合并到 `main`；PR #28 建立 Liquid Glass 学习工作区，PR #29 完成动效、光效、导航指示器和下拉定位修复；两次合并后的 CI 均成功。
- `main` 已通过 PR #58 合并 #33 学习教学页面；本功能分支全量回归为 179 tests，Ruff、format、Mypy、Streamlit smoke、Secret Scan、黄金集校验、Prompt dry-run 和依赖审计全部通过。
- `localhost:8511` 已实际验收 1440×1000 与 390×844：诊断失败保留原回答、重试、错题详情、安排复习、复测排期、标记掌握、进度更新和移动端侧栏交互均通过；未触碰个人 `8501`。
- 无费用评测验证：黄金集 20/20 案例结构有效且人工复核通过；Prompt v0.2 dry-run 渲染 20/20；Fake v0.1 全量管道 20/20 自动检查通过，未发起网络调用。
- 真实运行 `deepseek-evaluator-v0.1-20260824T004542Z`：模型为指定实验模型，935/452 tokens，调用成功但自动检查 0/1；模型提取到 4 条证据，却额外记录了未列入覆盖点的缺口，导致 `fragile`/`re_explain`，与该 strong 黄金案例的 `solid`/`practice` 标准不符。
- 随后的两次受控调用 `20260824T005050Z`、`20260824T005448Z` 均为 `LLM_OUTPUT_INVALID`，0/0 tokens；未自动重试。
- 诊断后确认模型曾返回 JSON 但类型不稳定（`limitations` 字符串、置信度文字），已通过显式 JSON 类型指令修复。
- `deepseek-evaluator-v0.1-20260824T011349Z`：4/4 成功、自动检查 4/4 通过、3936/1233 tokens；四个场景分别得到 `solid/practice`、`fragile/re_explain`、`fragile/review`、`not_evident/re_explain`。
- 完整 20 案例真实调用均成功；多轮回归自动检查在 17–19/20 之间波动，最新运行 `deepseek-evaluator-v0.1-20260824T015320Z` 为 20/20 结构成功、17/20 自动通过、25274/7049 tokens。
- 剩余失败均为语义置信度或 gap 边界的随机波动，未出现新的 API、JSON、Schema 或证据摘录故障。

## Resume Point

`main` 已包含 #33 可操作教学闭环；当前功能分支已把 #35 错题本、#37 复习复测、反馈/纠正和长期状态进度页接到既有服务契约，并通过 Fake 浏览器闭环验收。PR #59 已关联 #35/#37/#39 并等待审核；合并后才更新这些阶段的正式完成度。随后仍需真实语义验收，并按 `docs/roadmap/SEVEN_DAY_TRIAL_READINESS.md` 开始实际 7 天试用。

GitHub 工作项：

- [Prompt v0.2 语义稳定性实验](https://github.com/njr070907/AI_SelfLearner/issues/24)
- [20 条黄金案例人工复核](https://github.com/njr070907/AI_SelfLearner/issues/25)
- [自动结果与人工结论校准报告](https://github.com/njr070907/AI_SelfLearner/issues/26)
- [完整自学 MVP 计划](https://github.com/njr070907/AI_SelfLearner/blob/main/docs/roadmap/FULL_SELF_STUDY_MVP_PLAN.md)
- [MVP 进度面板](https://github.com/njr070907/AI_SelfLearner/blob/main/docs/roadmap/MVP_PROGRESS.md)
- [完整自学 MVP 工作项 #31–#39](https://github.com/njr070907/AI_SelfLearner/issues?q=is%3Aissue+label%3Aenhancement)
