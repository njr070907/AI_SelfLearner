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
