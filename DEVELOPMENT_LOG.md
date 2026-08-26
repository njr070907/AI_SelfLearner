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
- #51 修正真实模式 UI：DeepSeek 模式隐藏 Fake 场景选择器，重试仍由用户显式触发，侧栏/系统页显示固定模型状态；新增 Streamlit 回归后离线测试为 144 个。该项属于阶段 5 应用接线的收尾，不单独提高总进度。
- 无费用协议回归：黄金集 20 个案例结构有效且人工复核通过，Prompt v0.2 dry-run 渲染 20/20，Fake v0.1 全量管道 20/20 自动检查通过；未发起真实网络调用。
- 新增 `scripts/seed_fake_workspace.py`：用稳定幂等键生成 4 个 Fake 学习会话、3 个错题、3 个到期复习项目和一次用户纠正，供前端合作者本地验收页面；新增契约测试，重复运行不会增加记录，不访问网络。

## 2026-08-26

- 完成 Prompt v0.2 真实受控实验，固定 `deepseek-v4-flash-vision-exp`、零自动重试。初始 4 条发现 `severity` 枚举和强答案 gap 边界问题；随后完成置信度、条件覆盖和 `evidence_id` 字符串约束修复。
- 最终批量运行 `deepseek-evaluator-v0.2-20260826T020209Z` 为 18/20 结构成功、18/18 自动通过；两条仅为 `evidence_id` 类型错误，定向复测 `020421Z` 为 2/2 自动通过。所有结果仍需要人工语义复核，v0.2 暂不设为默认。

- 根据产品负责人补充的 MVP 要求，新增本地资料库基础版：SQLite `documents` 迁移保存元数据，文件字节保存在 `data/documents/`；服务层完成上传、读取、重命名、替换和删除，并拒绝路径穿越、空文件、不支持类型和超过 20 MB 的文件。
- Streamlit 新增“资料库”导航和页面，支持全部资料列表、下载、Markdown/TXT 预览、重命名、替换和删除；不把 PDF 自动解析、RAG 或向量数据库提前带入本次范围。
- 资料库单元、迁移、上传和页面空状态测试通过；全量回归 186 passed，Ruff 与 Mypy 通过。MVP 进度面板新增阶段 7，并按新范围重分配权重为约 90%。

- PR #58 已合并 #33 学习教学页面；阶段 1 按用户可操作口径从 50% 更新为 100%，正式 MVP 进度由约 56% 更新为约 66%。
- 功能分支 `feat/35-37-39-self-study-loop` 完成 #35 错题本：列表、筛选/排序、可追溯证据详情、状态切换、安排复习和按同一知识点重新作答。
- 完成 #37 复习队列与复测：到期队列、后端调度结果、失败保留回答/显式重试、下一题和标记掌握；服务契约没有手动延后 API，因此只展示禁用入口与原因，不从 UI 计算日期或直写数据库。
- 集成 #39 Fake 自学闭环：今日入口、教学诊断反馈/用户纠正、错题、复习和长期状态进度连通；新增 7 天试用准备清单，但没有声称已完成真实 7 天。
- 在团队专用 `localhost:8511` 完成 1440×1000 与 390×844 实际浏览器验收；诊断失败原回答保留、重试、错题定位、复测排期、掌握持久化、进度更新、深色主题和移动侧栏均通过，桌面与移动端无横向溢出。个人 `8501` 未被启动或停止。
- 浏览器插件在当前环境不可用，使用本地 Playwright 做等价实际浏览器交互；仅出现 Streamlit iframe 的已知 feature-policy 警告，没有应用错误或页面异常。
- 全过程保持 Fake Provider、零网络模型调用、零费用；未修改数据库迁移、Provider Factory、Mastery Engine、Learning Policy、API Key、`.env` 或真实模型配置。
- 最终本地回归通过：179 tests、Ruff、format、mypy、Streamlit smoke、Secret Scan、20 条黄金集结构校验、20 条 Prompt dry-run（Provider 调用 0）和依赖审计（无已知漏洞）。
- 创建 PR #59，关闭关联 #35/#37，并把 #39 保留为“已准备进入 7 天试用”的阶段关联；真实 7 个自然日发生前不关闭 #39。
- PR #59 已合并到 `main`（合并提交 `7549113`）。在合并后的 `main` 上复核 179 tests、Ruff、format、Mypy、Streamlit smoke、Secret Scan、20 条黄金集结构校验和 20 条 Prompt dry-run 均通过；正式进度更新为约 89%。
- 合并后阶段 1–4 的用户路径计为完成，阶段 6 的 Fake UI 全链路/启动/错误恢复部分计为 50%；剩余为真实 DeepSeek 语义验收、发布边界和至少 7 个自然日连续试用。
- 基于既有 `deepseek-evaluator-v0.1-20260824T015320Z` 运行记录完成无费用中间校准报告：20/20 结构成功、17/20 自动通过，3 个差异集中在强答案边界和置信度区间；未发起新的真实调用。
- 将主运行 `020209Z` 与定向复测 `020421Z` 合并为 v0.2 最终 20 条结果，生成 `docs/mastery-protocol/V0_2_REVIEW_DRAFT.md` 与 `V0_2_AI_INITIAL_REVIEW.md`。机器辅助检查显示四类场景均无类别串线、自动量表 20/20 通过；人工结论、差异分类和发布决定仍保持待确认。
- 完整回归再次通过：186 tests，Ruff 与 `git diff --check` 通过；提交 `fb89f67` 已同步到 `origin/main` 与协作分支。
- 完成试用前隔离环境预检：`tmp/trial-preflight.db` 从 0 迁移到 5，Fake 种子生成 4 条历史/3 个知识状态/3 个错题/3 个到期复习；健康检查全部 healthy，v0.2 dry-run 20/20 且零网络、零费用。该结果已写入 7 天试用准备清单，不替代真实试用。
- 增加 `V0_2_AI_SUGGESTED_REVIEW.md`，按 20 个 `case_id` 给出 AI 初审候选结论和人工重点关注项；未填写人工复核列，未改变 v0.2 发布门槛。
- 根据产品负责人复核意见升级 Mastery Protocol：`no_clue` 表示“完全未掌握”，`re_learn` 表示“重新学习”；协议/策略版本升至 v0.3，UI、黄金集、Schema、测试和旧数据库读取兼容同步更新。第 4 条人工结论改归类为 `mastery/action` 偏差。
- v0.3 完整回归通过：187 tests、Ruff、Mypy；Fake 20/20 自动通过，新的 `no_clue/re_learn` 已在真实应用组合根生效，旧 v5 数据库追加写入预检通过。
- 根据人工复核反馈升级 Mastery Protocol v0.4：只要 `possible_misconceptions` 有明确原答证据，掌握等级保持 `fragile`，推荐动作统一为 `re_learn`，不再使用 `review` 作为默认修复动作；更新黄金集、UI 回归和确定性策略测试。
- 根据产品负责人对第 14 条的复核意见升级 Mastery Protocol v0.5：学习者明确说“忘记/忘了/记不全/想不起来”时先 `review`，复习回答再重新计算掌握程度，掌握很低时才转 `re_learn`；新增答案文本分流和策略测试。
- v0.5 回归通过：189 tests、Ruff、format、Mypy；Fake 黄金集 20/20 自动通过，含明确忘记措辞的案例先输出 `review`，其余错误概念仍输出 `re_learn`。
- v0.6 回归通过：190 tests、Ruff、format、Mypy；Fake 黄金集 20/20 自动通过，错误概念和忘记类回答先输出 `review`，复习阶段低掌握才输出 `re_learn`。
- 根据产品负责人进一步确认，错误概念也必须先复习再复测；升级 Mastery Protocol v0.6，增加 `review_phase`：复习后仍为 `no_clue`/`fragile` 或仍有误区时才输出 `re_learn`，复习后证据充分则进入 `practice`。
- 完成 20 条 Prompt v0.2 真实结果人工语义复核：20/20 已由产品负责人在聊天中逐条确认；更新 `V0_2_REVIEW_DRAFT.md`、`REAL_SEMANTIC_CALIBRATION.md`、进度面板和 Backlog，阶段 5 从 75% 更新为 90%，总 MVP 进度约 92%。剩余为发布边界确认和至少 7 个自然日连续试用。
- 根据试用反馈修正学习入口：用户先确定主题，进入学习准备阶段，阅读资料库/教材并记录三条要点，勾选完成后才进入费曼理解检查；新增资料库文本预览/PDF 下载入口和页面回归测试。全量回归更新为 191 tests，Fake 试用环境继续保持零网络、零付费调用。
