# Current

## 当前里程碑

Sprint 1：用真实 Provider 验证 `evaluator-v0.1` 能否区分充分理解、部分理解、明确误区和证据不足；并行把学习工作区扩展成完整自学 MVP。

## MVP 总进度

**约 88.1% / 100%（按常规教学最终验收口径重新估算）** · 工程底座、错题、复习、反馈和资料库 CRUD 已完成；常规教学入口、章节式课程、互动进度持久化、课程完成小结、基础跨课程学习报告、英文中文化保护和 AI 主题选择已落地，但来源内容质量、报告深化、发布边界和连续试用仍待完成。预计还需 **4–7 个有效工作日**（含验证和发布准备），另需真实经过至少 7 个自然日；自动化测试不能替代连续试用。

完整阶段权重和计算方式见 [`docs/roadmap/MVP_PROGRESS.md`](docs/roadmap/MVP_PROGRESS.md)。这是按最终用户可正常使用的功能验收权重，不按代码量或已经经过的时间计算；当前 88.1% 不代表日历时间已经过去 88.1%。

## 当前状态

- 分支：`codex/accept-self-study-mvp`（已完成本轮本地模型路由、Provider 契约、中文输出保护、AI 主题候选和教学表单选择化）
- 任务：已把“学习”入口改为常规教学、增加独立“掌握检测”入口，并新增教学章节位置、互动答案、课程完成状态、数据库课程列表恢复、课程完成小结、后端统一课程报告、本地用户数据导出和显式 PDF 视觉读取模式。本轮已接入 Ollama 三模型路由：本地 GPT-OSS 负责教学/证据，Qwen 4B 负责互动小题和主题候选，Qwen 0.8B 负责英文/中英混排资料翻译；视觉页面仍固定走 DeepSeek。英文资料上传或替换成功后会立即进入后台翻译队列，结果按文件哈希缓存；生成课程时优先使用已完成译文，翻译未完成或失败则直接使用原文，不阻塞课程保存。教学生成现要求学习字段使用简体中文，若模型仍返回英文会自动进行一次有界语言修复，失败后保存中文资料导读草稿。学习页不再要求用户填写主题：默认分析所选资料，后台生成 AI 主题候选，用户从候选中选择；分析等待或失败时提供明确标注的临时主题，不阻塞课程保存。学习目标也改为预设选项（含“由 AI 自动安排”），生成教学内容时在后台线程显示已用时间、预计剩余时间和超时等待状态，避免用户误以为页面卡死。最新已将教学生成改为“自动修复→部分核验保存→资料导读草稿保存”的容错流程，视觉分卷页码可自动换算，报告会统计核验状态；原文证据保持可追溯。下一步是覆盖更多真实英文/公式资料、深化报告和完成发布验收。
 - 已新增并接通主题能力：`TeachingService.recommend_sources()` 按 AI 选定主题从资料库分卷中做本地文字抽样推荐，返回匹配分数、页码、命中词、置信度和选中的 document IDs；学习页默认使用推荐分卷，允许用户增删，低置信度时仍保留完整资料范围。`TopicSuggestionService` 将主题分析按资料哈希缓存并在后台运行；打开教学页时只抽样少量 PDF 页面，并复用本地缓存，避免整本教材阻塞页面。
- 本轮新增轻量本地角色代理层：规划角色先用 `OLLAMA_BALANCED_MODEL` 生成并校验知识依赖、核心事实、发现路径和按需视觉化建议；教学/题目/证据审查/翻译/视觉规划角色的职责以 manifest 明确，但不引入 `.pi` 运行时或隐藏多代理循环。规划模型失败时立即使用确定性路线，课程仍然生成；掌握判断仍由后端 Mastery Engine 和 Learning Policy 负责。
- 约束：仓库默认 Fake；Ollama 本地模式不需要 API Key；DeepSeek 真实运行必须显式确认；每个案例零重试；任何成功结果仍需人工语义复核。

## 最近一次修复

- 教学证据错误不再直接触发 `TEACHING_SOURCE_EVIDENCE_INVALID` 并终止课程。系统会规范化页码、处理分卷页码偏移、匹配分页原文、尝试一次证据修复；仍无法确认时保存 `partial` 或 `draft` 课程并在页面显示提示。
- Provider 超时、不可用、结构缩略、跑题或内容质量不足时，会保存本地资料导读草稿，保证学习报告和课程入口可用；只有资料不可读且没有任何可生成内容时才允许失败。
- 最近验证：257 tests passed；Ruff、format、Mypy passed；Streamlit 教学 E2E 与 Streamlit smoke test passed。

## 最近验证

- PR #3–#29 均已按 PR + CI 流程合并到 `main`；PR #28 建立 Liquid Glass 学习工作区，PR #29 完成动效、光效、导航指示器和下拉定位修复；两次合并后的 CI 均成功。
- 当前工作树已接入“资料库上传 → 学习入口生成课程 → 章节阅读 → 互动小测 → 保存进度 → 刷新后从我的课程继续 → 可选掌握检测”的常规教学入口；掌握检测为独立功能。资料库超过 20 MB 的 PDF、Markdown、TXT 现在会默认安全分卷导入，教学提取会安全识别常见文本编码并按页面/片段保留来源；课程报告计算已移入后端 typed service；系统页已可生成本地导出包。全量回归为 235 tests，Ruff、format、Mypy 已通过。
- 本地导出命令 `scripts/export_user_data.py` 已接入：导出用户范围内的原始事件、派生状态、课程/复习/错题数据和资料文件，带清单、Schema 版本与校验；不上传网络。
- 当前分支隔离预检已验证迁移 `0 -> 7`、Fake 种子幂等和健康检查 `liveness/readiness/provider=healthy`；该预检不替代真实 7 天试用。
- 发布前再次预检已在新隔离库确认迁移 `0 -> 7`、Fake 种子幂等、健康检查 `7/7` 和 Streamlit smoke HTTP 200；网络调用 0、付费调用 0，仍不替代真实 7 天试用。
- 最新 `scripts/smoke_streamlit.py` 实际启动通过（临时端口 54898），确认当前代码可由真实 Streamlit 进程提供 HTTP 200。
- 在明确授权后，固定 `deepseek-v4-flash-vision-exp` 真实 Provider 适配器先发现字段变体，随后经归一化修复完成一次端到端落库：4 类章节、3 道互动题、来源引用和 `teaching-lesson-v0.2` 均有效；该合成数学案例已完成单案例人工语义复核并通过，但全量真实资料语义复核和发布边界仍未完成。
- 第二个真实教学案例使用仓库 PRD 文档时先后发现 `LLM_OUTPUT_TRUNCATED` 和章节缺少 `section_type` 两个真实变体；已分别修复输出上限、Prompt 和受限归一化。修复后的新请求成功落库，PRD 内容已完成人工语义复核并通过；两个受控真实教学案例均通过，但更广泛资料验收和发布边界仍未完成。
- 2026-08-26 对真实 `Calculus.pdf` 分卷做了两次新的单案例教学验收：第 1 分卷因受限前 30,000 字不足以支持 `limits` 主题而被 `TEACHING_CONTENT_NOT_RELEVANT` 安全拒绝；第 2 分卷成功生成并落库，4 类章节、3 道互动题、答案选项和来源引用均通过初步检查。该结果确认跑题保护有效，也确认大资料分卷需要用户选择正确主题范围；不提高总进度，仍需更广泛语义复核。
- 本轮新增 PDF 视觉输入 fallback：文字层乱码/不可提取时可显式开启视觉读取，按主题选择最多 6 页、用 PyMuPDF 渲染为受限 JPEG，并通过 DeepSeek Chat Completions 的图片内容块发送；默认 Fake/文字路径不变。教学服务新增乱码、章节过短、缺少例子和互动题数量质量门槛，文本资料上传阶段会拒绝无法安全识别的编码，避免半成品课程落库。
- 视觉适配器离线契约和 PDF 渲染测试通过；使用临时生成的无敏感单页英文 PDF 做了一次固定 `deepseek-v4-flash-vision-exp` 真实能力验证，端点接受图片并返回结构化 JSON（未保存课程、未发送用户资料）。全量回归为 235 tests，Ruff、format、Mypy 通过；仍需真实中文教材/公式页面人工复核，不能把单页能力验证当成发布结论。
- 本轮完成本地 Ollama Provider 接入和路由验证：`gpt-oss:20b` 用于教学内容与证据提取，`qwen3.5:4b` 用于互动小题，`qwen3.5:0.8b` 写入配置作为轻量辅助模型；本地模型通过 `127.0.0.1:11434/v1` 调用，零自动重试，输出先经过 JSON 解析和既有 Schema 校验。Ollama 模式可在没有 API Key 时启动；只有显式视觉请求才尝试固定 DeepSeek。
- 教学资料处理已增强为分页 source units：长 Markdown/TXT 会分块并安全识别常见编码，PDF 会保留页码并按主题选取相关页和邻近上下文；真实 Provider 若返回缩略课程，会触发一次结构补全，缺少引用时再触发一次 evidence-only 修复。修复请求只能从已提供资料复制引文，不能绕过来源校验；全量回归为 234 tests。20B/4B 在当前纯 CPU 机器上的真实生成速度仍需单独优化，不能把超时当作内容质量结论。
- 随后补充验证：常见编码上传与超限分卷、主题推荐、文字 PDF 页码证据和结构补全回归均通过；全量回归更新为 235 tests。
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

`origin/main` 已包含 PR #59 和资料库/基础教学提交；当前分支已新增学习入口分离、章节导航、教学活动尝试、课程进度迁移、“我的课程”恢复列表、课程完成小结、基础跨课程报告、跑题保护、主题自动推荐前后端接通、本地 Ollama 三模型路由和中文输出保护。下一步是覆盖更多英文/公式资料、深化报告、完成真实发布边界确认，并按 `docs/roadmap/SEVEN_DAY_TRIAL_READINESS.md` 开始实际 7 天试用。

本轮已在当前分支接入 `LocalRoleAgentLayer` 和 `TeachingPlan`：下一次继续时先查看角色层单测与本地模型实际响应，再决定是否把视觉建议扩展为可选图示渲染；不要安装或复制 `amosblomqvist/learn` 的 `.pi` 配置。

GitHub 工作项：

- [Prompt v0.2 语义稳定性实验](https://github.com/njr070907/AI_SelfLearner/issues/24)
- [20 条黄金案例人工复核](https://github.com/njr070907/AI_SelfLearner/issues/25)
- [自动结果与人工结论校准报告](https://github.com/njr070907/AI_SelfLearner/issues/26)
- [完整自学 MVP 计划](https://github.com/njr070907/AI_SelfLearner/blob/main/docs/roadmap/FULL_SELF_STUDY_MVP_PLAN.md)
- [MVP 进度面板](https://github.com/njr070907/AI_SelfLearner/blob/main/docs/roadmap/MVP_PROGRESS.md)
- [完整自学 MVP 工作项 #31–#39](https://github.com/njr070907/AI_SelfLearner/issues?q=is%3Aissue+label%3Aenhancement)
