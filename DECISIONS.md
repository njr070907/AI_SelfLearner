# Decisions

## 2026-08-24 — 真实 Provider 使用结构化输出

- 使用 OpenAI Responses API 的 Pydantic 结构化输出，将返回值直接约束为 `ProviderObservation`。
- Provider 只提取证据；`DemoMasteryEngine` 和 `DemoLearningPolicy` 仍分别负责状态判断与下一步动作。
- 第一版只实现评估能力，不为尚未版本化的问题生成 Prompt 偷加隐式行为。

## 2026-08-24 — 付费调用默认关闭

- Fake 是默认运行模式。
- 真实模式需要显式 Provider、API Key、非 Fake 模型名和付费确认标志。
- 单案例零重试，首轮默认 1 条，避免网络波动造成隐性费用。

## 2026-08-24 — DeepSeek 使用 Chat Completions JSON Output

- `deepseek-v4-flash-vision-exp` 不再走 OpenAI Responses API。
- 使用 `https://api.deepseek.com` 的 OpenAI 兼容 Chat Completions 和 `response_format={"type":"json_object"}`。
- DeepSeek 返回的 JSON 先在本地解析，再通过 `ProviderObservation` 严格校验；结构不完整不得进入 Mastery Engine。

## 2026-08-24 — 真实评估失败时停止盲目重试

- 真实运行固定为单案例、零自动重试；成功结果也必须人工语义复核。
- 一次成功调用暴露了 Prompt v0.1 的范围误判：未列入 `coverage_points` 的高级理论不能自动成为 gap；适配器增加范围约束，但暂不冒充 Prompt v0.2。
- 连续两次后续调用返回 `LLM_OUTPUT_INVALID` 且 0/0 tokens。已经完成受限 JSON 恢复与离线验证后仍失败，因此停止更多付费调用，等待模型/账号/接口稳定性确认。

## 2026-08-24 — DeepSeek 类型约束与 4 场景基线

- 不放宽 `ProviderObservation` 的严格 Schema；将数组和数值类型直接写入 DeepSeek JSON 指令。
- 将失败诊断限制为字段路径和错误类型，不保存模型原文、学习者答案或密钥。
- 类型修复后 4 个场景自动检查全部通过；完整 20 条属于新增付费范围，需单独批准。

## 2026-08-24 — 20 案例回归后的停止点

- 完整 20 案例已验证 Provider 管道：所有调用均返回可解析且 Schema 合法的观察。
- 自动检查在多轮运行中为 16–19/20，剩余差异集中在强答案的额外 gap 和 partial/insufficient 的置信度边界。
- 不继续用重复付费调用追逐 20/20；先进行 Prompt v0.2 或确定性校准实验，并保留所有运行证据供人工复核。

## 2026-08-25 — Prompt v0.2 先做可追踪候选，不替换默认版本

- 新增 `evaluator-v0.2` 候选 Prompt，继续输出 `provider-observation-v0.1`，重点改为逐 `coverage_points` 内部检查，减少额外 gap、重复 gap 和把孤立公式当作正向证据。
- CLI 通过 `--prompt-version v0.2` 显式选择候选版本；默认仍使用 `v0.1`，运行记录保存 Prompt 版本和内容哈希。
- 先完成 Fake/dry-run 和固定案例对照设计，再决定是否进行真实 DeepSeek 调用；不因候选版本已经能渲染就宣称语义质量已改善。

## 2026-08-25 — 完整自学 MVP 采用前后端分工

- 当前 Codex 负责后端与学习核心：数据模型、事件历史、Mastery Engine、Learning Policy、Provider、服务契约、测试和 CI。
- GitHub 合作者主要负责前端 UI：Streamlit 页面、组件、交互、主题/响应式和页面验收；前端不直接访问 SQL 或 Provider，也不复制掌握度和复习规则。
- 先通过 Fake fixtures 锁定 typed service models，再并行实现学习、错题、复习和进度页面；真实 `deepseek-v4-flash-vision-exp` 只在 Fake 闭环稳定后做小范围验证。
- 完整自学 MVP 的范围、26–39 个工作日估算、GitHub Issues #31–#39 和停止条件记录在 `docs/roadmap/FULL_SELF_STUDY_MVP_PLAN.md`。

## 2026-08-25 — 复习调度先采用可解释的 1/3/7 天规则

- 错题成功生成后立即进入到期队列，初始间隔为 1 天；正确复测推进到下一个间隔，部分正确回到 3 天，错误回到 1 天。
- Provider 失败或结构无效只记录复测失败，不改变原定到期时间；相同幂等键不会重复调用 Provider。
- 复测调度是 Learning Policy 的可替换实现，不把一次正确复测等同于永久掌握；原始回答、观察和调度事件都保留。

## 2026-08-26 — AI 初审不能关闭人工语义验收

- 对 v0.2 最终 20 条结果可以做自动结构、场景形态和 rubric 一致性检查，但不能据此填写产品负责人的“人工结论”。
- `V0_2_AI_INITIAL_REVIEW.md` 只记录可复现的机器检查和待确认项目；在 20 条人工复核完成前，`evaluator-v0.2` 不设为默认生产协议。

## 2026-08-26 — 人工复核使用用户可读的掌握标签

- 人工复核记录同时写产品中文标签和协议枚举：`no_clue` 显示为“完全未掌握”，`re_learn` 显示为“重新学习”。
- v0.2 的 `not_evident/re_explain` 只作为历史兼容值读取，不作为新协议输出。

## 2026-08-26 — 完全未掌握与重新学习改为 v0.3 正式枚举

- 产品正式枚举改为 `no_clue`（完全未掌握）和 `re_learn`（重新学习），不再把 `not_evident/re_explain` 作为新协议输出。
- `mastery-protocol-v0.3-golden-baseline` 与 `learning-policy-v0.3-golden-baseline` 承载该语义变更；旧数据库和旧事件在读取时做兼容映射，避免破坏历史证据。
- v0.2 真实运行记录仍作为历史实验保存；人工复核时，旧枚举与 v0.3 正式枚举不一致要归类为 `mastery`/`action` 偏差。

## 2026-08-26 — 明确错误概念统一进入重新学习

- 当 `ProviderObservation.possible_misconceptions` 非空且有原答证据时，掌握等级仍按保守规则记为 `fragile`，但 Learning Policy 不再推荐 `review`，统一输出 `re_learn`。
- 原因是明确错误概念不是普通复习需求，而是需要先重建概念，再用新例子验证；错误证据仍完整保留在事件历史和错题记录中。
- 该动作语义变更升级为 `mastery-protocol-v0.4-golden-baseline` / `learning-policy-v0.4-golden-baseline`；v0.2 的 `review` 结果保留为历史输出，人工校准归类为 `action` 偏差。

## 2026-08-26 — 自述忘记先复习，再决定是否重新学习

- 当学习者明确说“忘记”“忘了”“记不全”或“想不起来”时，第一步动作固定为 `review`，而不是立即把一次记忆缺失当作完全未掌握。
- `review` 必须附带复习题或检查点；复习回答再次经过 Mastery Engine，掌握很低时再输出 `re_learn`，否则按新的证据继续决定 `practice` 或下一步。
- 第 14 条人工复核按此规则改为 `fragile / review`；协议/策略版本升级为 `mastery-protocol-v0.5-golden-baseline` / `learning-policy-v0.5-golden-baseline`。

## 2026-08-26 — 错误概念也先复习再分流

- `possible_misconceptions` 非空时，初始动作也统一为 `review`，先让学习者核对错误概念并完成复习题；不能把一次错误回答直接等同于需要从头学习。
- 复习阶段通过 `review_phase` 标记区分：复习后仍为 `no_clue`/`fragile`、仍有缺口或误区时输出 `re_learn`；复习后证据充分则进入 `practice`。
- 该策略变更升级为 `mastery-protocol-v0.6-golden-baseline` / `learning-policy-v0.6-golden-baseline`，已同步更新 20 条黄金量表和人工复核记录。
- 20 条 v0.2 真实结果已完成逐条人工语义复核并确认；v0.6 作为当前 Mastery Protocol golden baseline，人工校准工作完成，但不自动授权将 `evaluator-v0.2` 设为默认生产协议，仍需独立完成发布边界和连续试用验收。

## 2026-08-26 — 资料先生成导学，再进入诊断

- 资料库文件管理与教学生成分成两个服务：`DocumentLibraryService` 负责文件 CRUD，`TeachingService` 负责提取文字、调用 Teaching Provider、校验 `TeachingLesson` 并保存来源引用。
- 教学内容必须经过 `concept`、`mechanism`、`boundary`、`example` 四类结构化章节；Provider 只整理资料，不能直接写入掌握等级，后续仍由回答证据、Mastery Engine 和 Learning Policy 判断。
- 默认 Fake Provider 生成确定性免费导学；真实模式只允许 `deepseek-v4-flash-vision-exp`，并且必须显式允许付费调用。扫描版 PDF 没有 OCR 支持，RAG/向量数据库留到 MVP 之后。

## 2026-08-27 — 本地 Ollama 三模型按职责路由

- 增加 `ollama` Provider 模式，默认通过 `http://127.0.0.1:11434/v1` 访问本机服务，不要求 API Key、不自动重试，也不把本地模型输出直接当作掌握结论。
- `gpt-oss:20b` 负责来源约束的常规教学内容和回答证据提取；`qwen3.5:4b` 负责互动小题生成；`qwen3.5:0.8b` 写入配置，作为后续翻译、摘要和元数据等轻量任务的预留模型。
- 扫描版或乱码 PDF 的视觉路径仍固定使用 `deepseek-v4-flash-vision-exp`，只有用户显式开启视觉模式并满足既有付费许可时才调用；本地文字教学不依赖该 Key。
- 所有模型返回值继续经过本地 JSON 解析、既有 Pydantic Schema、Mastery Engine 和 Learning Policy；Provider 只提供证据，不能绕过确定性业务规则。

## 2026-08-27 — 教学证据采用“先修复、再降级保存”

- `TEACHING_SOURCE_EVIDENCE_INVALID` 不再作为正常课程生成的终止条件。教学服务先规范化自然语言页码、0/1 起始页码和资料分卷原始页码，再按分页原文和视觉页面集合匹配；Provider 只接受一次证据修复请求。
- 无法完全核验的课程仍保存，并在课程 JSON 中记录 `grounding_status`：`verified`、`repaired`、`partial` 或 `draft`。UI 和学习报告明确显示状态，不把部分核验课程伪装成已核验课程。
- Provider 超时、不可用、结构缩略、跑题或质量不足时，使用资料原文构造确定性的资料导读草稿并保存。真正阻止的范围收窄为：没有资料、资料不可读且无任何可用内容，或无法生成最低可用课程结构。

## 2026-08-27 — 英文资料先翻译，原文仍是证据唯一来源

- 在 Ollama 模式下，教学服务先用 `OLLAMA_FAST_MODEL`（默认 `qwen3.5:0.8b`）检测并分段翻译英文/中英混排 source units，再把中文译文和英文原文的双语上下文交给教学模型。
- `TeachingSourceUnit.text` 始终保存原文，新增的 `translated_text` 只是理解辅助；章节和互动题的 `evidence.quote` 仍必须从原文逐字复制，页码继续绑定原始 source unit。
- 翻译是 best-effort 派生步骤：单个片段失败、模型不可用或返回乱码时，课程继续使用英文原文生成，并在课程 JSON/UI 中记录 `translation_status`、模型名和失败片段数；不因翻译故障拒绝生成报告。
- 翻译仅影响教学内容的可读性，不改变 Mastery Engine、Learning Policy 或长期掌握结论。
- 上传/替换入口负责排队，教学生成入口只读取缓存：翻译任务使用进程级单线程执行器和原子 JSON 写入，避免 Streamlit rerun 丢失任务或让用户等待；缓存不存在/仍在运行时直接使用原文。

## 2026-08-27 — 主题由 AI 提炼，用户只选择不手写

- 学习页不再提供“填写主题”输入框。页面默认分析用户选定的资料，由 `TopicSuggestionProvider` 返回结构化候选（主题、摘要、关键概念、置信度），用户从下拉列表选择后再生成课程。
- 主题候选按所选资料的 document ID、文件名和 SHA-256 形成缓存键，后台单线程生成，避免页面刷新丢失任务；已有本地 `TopicSourceSelector` 负责把选定主题映射到相关分卷，用户仍可调整最终来源范围。
- 主题分析属于辅助能力，不得成为课程生成的硬阻塞：分析等待或模型失败时显示“临时主题”并允许继续生成，缓存完成后刷新即可使用 AI 候选；临时选项和英文主题标签都明确标注，不能伪装成 AI 结论。

## 2026-08-27 — 教学字段强制中文但保留原文证据

- `TeachingRequest.output_language` 固定为 `zh-CN`。Ollama/DeepSeek Prompt 和本地服务共同约束学习者可见字段使用简体中文，英文术语仅作为必要补充，`evidence.quote` 始终保留资料原文。
- 服务端对完整课程做中文比例检查；不满足时只允许一次有界语言修复，仍失败则保存中文资料导读草稿。翻译缓存拒绝纯英文结果，避免错误标注为已翻译。

## 2026-08-27 — 教学表单目标选择化与实时生成反馈

- “学习目标”不再允许自由填写，改为有限的学习意图选项；其中“不指定（由 AI 自动安排）”映射为 `learning_goal=null`，其它选项映射为稳定的后端提示语，避免任意文本污染课程 Prompt。
- 教学生成放入单线程后台任务，UI 每 0.5 秒更新进度条、已用时和预计剩余时长。估计值按 Provider 类型取保守上限（Fake 5 秒、Ollama 300 秒、远程 120 秒），超过后显示“仍在等待模型”，不伪造精确完成百分比，也不重复提交。

## 2026-08-27 — 吸收 learn 的教学方法但不安装 `.pi`

- 只吸收可迁移的教学思想：知识依赖、动机解释、从资料出发的发现路径、同构且包含真实误区的选择题，以及仅在结构更清楚时提出视觉化建议；不复制其 `.pi` 配置、运行时或子代理框架。
- 新增 `LocalRoleAgentLayer`，将 planner、teacher、quiz designer、source reviewer、translator、visual planner 的职责显式化。planner 可调用本地 Qwen 平衡模型生成 `TeachingPlan`，应用层负责 Pydantic 校验、主题/资料边界清洗和失败回退。
- `TeachingRequest` 携带已验证的 `TeachingPlan`；Ollama/DeepSeek 教学 Prompt 按依赖顺序组织常规讲解，并可填充 `why_it_matters`、`discovery_path`、`prerequisite_ids`。UI 以学习路线折叠区呈现计划，不把学习变成费曼答题流程。
- 角色层是增强项而非硬依赖：planner 超时、离线或返回无效 JSON 时使用确定性四段路线，课程和报告仍按原流程保存；AI 只产生候选信息，来源证据、课程状态、掌握等级和下一步动作继续由后端决定。
