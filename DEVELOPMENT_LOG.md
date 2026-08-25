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
