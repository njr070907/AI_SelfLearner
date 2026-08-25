# Development Log

## 2026-08-24

- 合并 PR #23：增加 GitHub 协作者交接手册、按 `--case-id` 的低成本案例复现、Prompt 实验/人工复核 Issue 模板，并通过 82 tests、Ruff、format、Mypy 和 Secret Scan。
- 创建 GitHub Issue #24（Prompt v0.2 实验）、#25（20 条黄金案例人工复核）和 #26（评测校准报告），作为下一阶段可领取工作。
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
- 诊断运行 `20260824T010509Z` 将失败精确分类为 `LLM_OUTPUT_SCHEMA_INVALID`；安全摘要显示 `limitations:list_type`，误区案例另有 `confidence:float_parsing`。
- PR #13–#15 已 squash 合并；增加字段路径/错误类型诊断，并在 DeepSeek 指令中明确数组与 0–1 数值类型。
- 类型修复后的单条 strong 运行 `20260824T011333Z` 自动检查通过；4 场景运行 `20260824T011349Z` 四案全部成功、自动检查 4/4 通过，3936/1233 tokens。
- 4 场景初步语义复核与黄金标准一致：strong→solid/practice，partial→fragile/re_explain，misconception→fragile/review，insufficient→not_evident/re_explain；仍保留人工复核标记。
- 完整离线回归更新为 81 tests、Ruff、format、Mypy 全部通过。
- PR #17–#21 已 squash 合并；补充 gap 去重、置信度边界和不确定孤立公式不计证据的规则。
- 完整 20 案例多轮真实回归均为 20/20 结构成功；自动检查分别为 16/20、17/20、18/20、19/20、17/20，说明剩余是实验模型的语义随机性。
- 最新运行 `deepseek-evaluator-v0.1-20260824T015320Z`：20/20 成功、17/20 自动通过、25274/7049 tokens；没有新的接口或结构化输出故障。
- 按安全边界停止继续完整付费重试，下一恢复点是 Prompt v0.2 稳定性实验和 20 条人工语义复核。
- 额度状态：`UNKNOWN`，环境没有提供可靠 remaining quota 信息。

## 2026-08-25

- 合并 PR #28：建立 Liquid Glass 学习工作区，拆分 UI 的主题、状态、展示和 shell 层，并增加 UI 单元/E2E 覆盖。
- 合并 PR #29：完成 UI 动效 token、页面进入/展开动画、CTA 光效、导航滑动指示器、下拉定位和深色主题对比度修复。
- 当前 `main` 的离线回归为 122 tests、Ruff、format、Mypy 全部通过；远程 main CI 成功。
- 增加 `evaluator-v0.2` 候选 Prompt、版本选择参数和零成本 dry-run；默认仍使用 v0.1，尚未发起新的真实付费调用。
- UI 代码已进入手工验收；Prompt v0.2 对照实验、20 条人工复核和校准报告仍是未完成的产品验证任务。
- 建立完整自学 MVP 路线图：创建 GitHub Issues #31–#39，明确当前 Codex 负责后端/学习核心、GitHub 合作者主要负责前端 UI、仓库所有者负责产品规则和最终验收。
- 将教学、错题、复习、长期状态和 7 天试用的阶段交付、服务契约、MVP 停止条件写入 `docs/roadmap/FULL_SELF_STUDY_MVP_PLAN.md`，并同步 `BACKLOG.md`、`CURRENT.md` 和 `docs/collaboration/HANDOFF.md`。
- 实现 #32 教学闭环后端：支持主回答与同一会话 follow-up，保存回答类型/序号、Fake 诊断、事件历史和重算状态；新增 2 个集成测试，离线回归更新为 124 tests。
- 新增 `docs/roadmap/MVP_PROGRESS.md`，固定显示 MVP 阶段位置、总体百分比和剩余工期；当前按验收能力估算为 41%，预计还需 15–24 个有效工作日。
- 实现 #34 错题本后端：新增 `wrong_items` 迁移、三类可追溯错误分类、列表/详情/状态服务和错题状态事件；新增 6 个集成测试，离线回归更新为 128 tests。
- 进度面板更新为 49%；当前阶段为错题本后端完成、等待前端页面接入，预计还需 13–21 个有效工作日。
- 实现 #36 复习调度后端：新增 `review_items`/`review_attempts` 迁移、1/3/7 天可配置调度、到期队列、复测成功/部分/错误结果、失败保留到期状态和幂等保护；新增 3 个集成测试，离线回归更新为 131 tests。
- 进度面板更新为 56%；当前阶段为复习后端完成、等待前端页面接入，预计还需 11–18 个有效工作日。
- 重新审计“最终用户可正常使用的完整 MVP”口径：旧的 56% 把后端接口、实验性真实 AI 和 UI 壳计入过多；新权重按用户验收重算为约 44%，后端已完成但前端未接入只计阶段一半，未合并代码不计入完成度。剩余调整为 15–24 个有效工作日（并行协作约 4–6 周），包含反馈/趋势、前端页面、真实 AI 发布边界、全链路集成和 7 天试用。
- 阶段 5 开始补 Provider Factory：Fake 仍为默认免费模式；真实模式只允许 `deepseek-v4-flash-vision-exp`，必须显式给予付费调用许可；真实评估器被包装进交互服务，题目生成暂用 Fake，避免在未完成题目 Provider 前混淆职责。新增 5 个离线安全测试，回归更新为 139 tests。
- #38 与 #45 合并后重新计算进度：阶段 4 后端能力达到约 60%，阶段 5 Provider 安全边界达到约 65%，总进度从重新校准的 44% 更新为约 53%；剩余估算调整为 12–20 个有效工作日。前端页面、真实语义验收和 7 天试用仍未计为完成。
- 新增 Fake 后端完整路径集成测试：教学→主回答诊断→追问→用户纠正→错题复习→复测→长期状态/趋势；回归更新为 140 tests，阶段 6 的后端假闭环验收计入，总进度更新为约 54%。
- #49 合并 Provider 应用接线：`app.py` 通过显式 `LLM_PAID_CALLS_ALLOWED` 选择 Fake/固定 DeepSeek 模式，默认不访问外部网络；离线回归为 143 tests，阶段 5 完成度更新为约 75%，总进度更新为约 56%。
