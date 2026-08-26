# Current

## 当前里程碑

Sprint 1：用真实 Provider 验证 `evaluator-v0.1` 能否区分充分理解、部分理解、明确误区和证据不足；并行把学习工作区扩展成完整自学 MVP。

## MVP 总进度

**约 92% / 100%** · **阶段 1–4 与阶段 7 资料库基础版已经完成，20 条真实结果人工语义复核也已完成**；Fake 全链路已验收，发布边界和连续试用仍待完成。预计还需 **1–3 个有效工作日**，另需真实经过至少 7 个自然日；自动化测试不能替代连续试用。

完整阶段权重和计算方式见 [`docs/roadmap/MVP_PROGRESS.md`](docs/roadmap/MVP_PROGRESS.md)。这是按最终用户可正常使用的功能验收权重，不按代码量或已经经过的时间计算；当前 92% 不代表日历时间已经过去 92%。

## 当前状态

- 分支：`codex/accept-self-study-mvp`（与 `origin/main` 同步，最新提交 `e3eada1`）
- 任务：DeepSeek `deepseek-v4-flash-vision-exp` 的评测基线、资料库基础 CRUD、教学、错题本、复习复测、反馈/长期状态页面、Fake 全链路和 20 条人工语义复核均已完成。发布边界和实际 7 个自然日试用仍未完成。
- 约束：默认 Fake；真实运行必须显式确认；每个案例零重试；任何成功结果仍需人工语义复核。

## 最近验证

- PR #3–#29 均已按 PR + CI 流程合并到 `main`；PR #28 建立 Liquid Glass 学习工作区，PR #29 完成动效、光效、导航指示器和下拉定位修复；两次合并后的 CI 均成功。
- 当前工作树已接入资料库基础版；全量回归为 190 tests，Ruff、format、Mypy、Streamlit smoke、Secret Scan、黄金集校验、Prompt dry-run 和依赖审计全部通过。
- `localhost:8511` 已实际验收 1440×1000 与 390×844：诊断失败保留原回答、重试、错题详情、安排复习、复测排期、标记掌握、进度更新和移动端侧栏交互均通过；未触碰个人 `8501`。
- 无费用评测验证：黄金集 20/20 案例结构有效且人工复核通过；Prompt v0.2 dry-run 渲染 20/20；Fake v0.1 全量管道 20/20 自动检查通过。另有单独记录的真实 v0.2 受控调用，不纳入无费用结论。
- 真实运行 `deepseek-evaluator-v0.1-20260824T004542Z`：模型为指定实验模型，935/452 tokens，调用成功但自动检查 0/1；模型提取到 4 条证据，却额外记录了未列入覆盖点的缺口，导致 `fragile`/`re_explain`，与该 strong 黄金案例的 `solid`/`practice` 标准不符。
- 随后的两次受控调用 `20260824T005050Z`、`20260824T005448Z` 均为 `LLM_OUTPUT_INVALID`，0/0 tokens；未自动重试。
- 诊断后确认模型曾返回 JSON 但类型不稳定（`limitations` 字符串、置信度文字），已通过显式 JSON 类型指令修复。
- `deepseek-evaluator-v0.1-20260824T011349Z`：4/4 成功、自动检查 4/4 通过、3936/1233 tokens；四个场景分别得到 `solid/practice`、`fragile/re_explain`、`fragile/review`、`not_evident/re_explain`。
- v0.1 的完整 20 案例真实调用均成功；多轮回归自动检查在 17–19/20 之间波动，基线运行 `deepseek-evaluator-v0.1-20260824T015320Z` 为 20/20 结构成功、17/20 自动通过、25274/7049 tokens。
- 剩余失败均为语义置信度或 gap 边界的随机波动，未出现新的 API、JSON、Schema 或证据摘录故障。
- 已将该轮自动结果与黄金量表的差异写入 [`docs/mastery-protocol/REAL_SEMANTIC_CALIBRATION.md`](docs/mastery-protocol/REAL_SEMANTIC_CALIBRATION.md)；报告已更新为人工复核完成后的校准记录，发布边界仍单独保留。
- 2026-08-26 使用固定 `deepseek-v4-flash-vision-exp` 完成 Prompt v0.2 受控实验：运行 `020209Z` 为 18/20 结构成功且 18/18 自动通过；两条是 `evidence_id` 类型错误，随后运行 `020421Z` 定向复测 2/2 通过。此前 3 条置信度/边界失败也在 `020147Z` 定向复测中 3/3 通过。
- v0.2 的协议约束和边界提示已修复并通过离线测试；产品负责人随后明确将“完全未掌握/重新学习”固化为 v0.3 的 `no_clue/re_learn`，在 v0.4–v0.5 完善错误概念和自述忘记的复习分流，并在 v0.6 统一为“先复习、复测后再决定是否重新学习”。
- 已完成 [v0.2 人工复核结果](docs/mastery-protocol/V0_2_REVIEW_DRAFT.md)：20/20 条逐案例确认，差异已按 v0.6 正式枚举和复习分流规则记录；不把自动通过冒充人工结论。
- 已生成 [v0.2 AI 初审摘要](docs/mastery-protocol/V0_2_AI_INITIAL_REVIEW.md)：20/20 自动量表通过，并按四种场景做了可追溯的形态检查；没有把 AI 初审写成人工语义结论。
- 已生成 [v0.2 AI 建议复核表](docs/mastery-protocol/V0_2_AI_SUGGESTED_REVIEW.md)：20 条逐案例候选结论和重点疑点，仍要求负责人回看原始证据后签字。
- 已将 Mastery Protocol 更新为 v0.6：`no_clue`=完全未掌握、`re_learn`=重新学习；明确错误概念和明确自述忘记都先推荐 `review`，复习后掌握仍低再转 `re_learn`，旧数据库值读取时兼容。
- 聊天内人工验收已完成 19/20：第 3、7、11、15、19 条的错误概念动作按 v0.6 记录为 `review`，第 4 条仍记录为 `mastery/action` 偏差，第 8、12 条正式记录为 `no_clue / re_learn`，第 9、13、17 条为 `solid / practice`，第 10、18 条为 `fragile / re_learn`，第 3、7、11、14、15、19 条为 `fragile / review`，第 16 条为 `no_clue / review`。

## Resume Point

`origin/main` 已包含 PR #59 的 #35 错题本、#37 复习复测和 #39 Fake 全链路集成；资料库基础版、反馈/纠正、长期状态进度页、桌面/窄屏交互、错误恢复和 20 条人工语义复核均已通过验收。随后仍需完成发布边界确认，并按 `docs/roadmap/SEVEN_DAY_TRIAL_READINESS.md` 开始实际 7 天试用。

GitHub 工作项：

- [Prompt v0.2 语义稳定性实验](https://github.com/njr070907/AI_SelfLearner/issues/24)
- [20 条黄金案例人工复核](https://github.com/njr070907/AI_SelfLearner/issues/25)
- [自动结果与人工结论校准报告](https://github.com/njr070907/AI_SelfLearner/issues/26)
- [完整自学 MVP 计划](https://github.com/njr070907/AI_SelfLearner/blob/main/docs/roadmap/FULL_SELF_STUDY_MVP_PLAN.md)
- [MVP 进度面板](https://github.com/njr070907/AI_SelfLearner/blob/main/docs/roadmap/MVP_PROGRESS.md)
- [完整自学 MVP 工作项 #31–#39](https://github.com/njr070907/AI_SelfLearner/issues?q=is%3Aissue+label%3Aenhancement)
