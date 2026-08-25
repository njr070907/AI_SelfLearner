# 完整自学系统 MVP 开发计划

> 这份计划把当前已经完成的工程底座，继续推进成一个可以真正完成“学习、诊断、错题、复习、反馈”的单用户自学产品。它是 GitHub 协作的共同工作说明，不替代 `docs/mastery-protocol/` 中更细的协议。

## 1. 当前判断

当前仓库已经具备可靠的工程地基：SQLite 与迁移、事件历史、Mastery Engine、Learning Policy、Fake Provider、真实 DeepSeek 适配器、结构化 Schema、评测 CLI、CI 和第一版学习工作区 UI 都已存在。最近一次离线回归为 134 个测试通过，Provider Factory 已把 Fake/固定 DeepSeek 模式和显式付费许可隔离，Prompt v0.2 也已经可以用 dry-run 做零成本实验。

但从“完整自学系统 MVP”看，按最终用户可正常使用的阶段权重计算当前约完成 **53%**：教学、错题、复习、反馈/趋势和 Provider 安全边界的后端能力已经建立，但用户页面、真实语义验收和 7 天试用还没有全部完成。每次开发都会同步更新 [`MVP_PROGRESS.md`](MVP_PROGRESS.md)，避免把代码量、测试数量或单个后端 PR 误当成产品完成度。当前最重要的是把 Mastery Protocol 变成用户能从头走到尾的一条完整路径。

## 2. MVP 范围

### 本次必须完成

1. 用户选择一个知识点并开始学习。
2. 系统给出教学卡片、例子或提示。
3. 用户用自己的话解释，系统可继续追问或给出练习。
4. 系统产生结构化诊断，保存原始回答、证据、误区和建议动作。
5. 错误或薄弱证据自动进入错题/薄弱项列表。
6. 用户可以在到期时复测，复测结果会改变下一次复习时间。
7. 用户可以修正 AI 的诊断，修正本身也作为事件保存。
8. 用户可以看到知识点的当前状态、重复误区和简单趋势。
9. 用 Fake Provider 走通端到端闭环，并用固定模型做小范围真实验证。

### 明确不做

- PDF 自动解析、RAG、向量数据库和正式知识图谱。
- 多用户登录、云端同步、权限体系和企业监控。
- 移动端原生 App、支付和复杂商业化功能。
- 多 Agent、自主改 Prompt、自动把模型输出直接写成掌握度。

默认前提是：单用户、本地 SQLite、文本优先，先支持高等数学和编程等结构清晰的知识点。以后需要扩大范围时，保留的事件历史和服务契约可以支持迁移。

## 3. 预计时间

按每天 4–6 个有效开发小时估算，总计 **27–42 个工作日，约 6–10 个日历周**。如果每天只有 2–3 小时，预计为 10–16 周。时间是可调整的工程估算，不是付费模型调用承诺。

当前已完成范围约 53%（这是最终功能验收权重，不是已经经过的时间），按剩余阶段拆分估算还需要 **12–20 个有效工作日**：前后端并行、每天 4–6 小时约 4–6 个日历周，每天 2–3 小时约 6–9 周。真实模型人工复核和 7 天试用可能拉长日历时间。

| 阶段 | 预计用时 | 后端/协议交付 | 前端 UI 交付 | 阶段验收 |
| --- | --- | --- | --- | --- |
| 0. 工程底座与契约 | 1–2 天 | 数据模型、服务边界、事件命名和状态语义 | 页面路由草图、状态清单、假数据约定 | 已完成 |
| 1. 自学教学闭环 | 4–6 天 | 教学会话、回答、诊断、追问和事件保存 | 学习页：知识点→教学→解释→追问/练习→反馈 | #32/#33；一个知识点完整走通 |
| 2. 错题本 | 2–3 天 | 错题模型、仓储、列表/详情/状态服务 | 错题列表、详情、重新作答入口 | #34/#35；错误证据可追溯 |
| 3. 复习与复测 | 2–3 天 | 到期队列、1/3/7 天间隔、复测结果和调度规则 | 今日复习队列、复测页、下一题和重新安排 | #36/#37；复测改变下一次时间 |
| 4. 反馈、长期状态与趋势 | 3–4 天 | 状态重算、重复误区、趋势和用户修正事件 | 进度/趋势/反馈解释 | #38；历史可重算，原始证据不丢 |
| 5. 真实 AI 发布与评测 | 3–5 天 | Provider 开关、固定 `deepseek-v4-flash-vision-exp`、Prompt 对照、校准和失败回退 | 真实结果展示与异常提示 | #24–#26；小样本人工复核后才进入产品路径 |
| 6. 全链路集成、7 天试用与发布验收 | 5–7 天 | E2E、迁移、启动、错误恢复、数据导出/重置边界和发布检查 | 四个入口的响应式/主题/交互验收 | #39；至少一轮连续 7 天试用 |

## 4. 明确的前后端分工

### 当前 Codex 负责后端与学习核心

- SQLite migration、领域模型、仓储和事件历史。
- Mastery Engine：根据证据判断状态，不接受模型一句话的最终裁判结果。
- Learning Policy：决定追问、练习、复习和重新解释等下一步动作。
- Fake Provider、DeepSeek Provider、Prompt、Schema 和评测工具。
- 教学、错题、复习、趋势服务的 typed models/API contracts。
- 单元测试、集成测试、E2E 测试、CI 和相关技术文档。

### GitHub 合作者主要负责前端 UI

- Streamlit 页面、组件和页面之间的用户流程。
- 学习、错题、复习、进度四个入口的布局、交互、加载/空/错误状态。
- 亮色/深色主题、窄窗口、键盘可用性和手工浏览器验收。
- 用 Fake fixtures 做 UI 开发，补页面级测试，并在 PR 中附验收记录。
- 不在 UI 中复制掌握度、复习间隔或错误分类等业务规则。

### 仓库所有者负责产品与验收

- 确定什么叫“理解/掌握”、什么证据足够、何时追问或复测。
- 复核数学语义和真实模型结果，批准协议或 Prompt 的产品方向。
- 对 UI 的学习体验做最终验收，必要时调整优先级。

## 5. 前后端协作契约

1. 前端只调用服务层的 typed models，不直接访问 SQL、migration 或 Provider。
2. 后端每个服务都提供 Fake fixtures 和最小调用示例，前端不需要 API Key 就能开发。
3. Provider 是“证据传感器”；Mastery Engine 判断学习状态；Learning Policy 决定下一步。
4. 任何 AI 诊断都必须保留原始回答、结构化证据、Prompt/模型版本和事件时间。
5. UI 只展示后端已经计算好的状态和动作；如果需要新字段，先在服务契约中补充。
6. 一个 PR 只做一个 Issue 的范围，分支使用 `feat/<issue>-short-name` 或 `fix/<issue>-short-name`，不直接推送 `main`。
7. 前端 PR 优先使用 Fake Provider；真实 DeepSeek 调用必须显式确认付费，固定模型为 `deepseek-v4-flash-vision-exp`，默认零重试。

### 最小服务接口方向

后端会逐步提供类似下面的服务能力（具体 Python 类型以实现为准）：

```text
start_learning(concept_id) -> LearningSession
submit_explanation(session_id, text) -> DiagnosisResult
list_wrong_items(filters) -> list[WrongItem]
get_review_queue(now) -> list[ReviewItem]
submit_retest(item_id, answer) -> ReviewResult
get_concept_state(concept_id) -> ConceptState
record_user_correction(event_id, correction) -> ConceptState
```

当前教学闭环已经落地为以下可供前端接入的字段：

- `SessionView.answer_count`：当前会话已经提交的回答数量；
- `SessionView.can_submit_follow_up`：只有成功诊断后才允许继续同一会话；
- `DiagnosisView.answer_type`：`main` 或 `follow_up`；
- `DiagnosisView.sequence_no`：回答在当前会话中的顺序；
- `submit_follow_up(...)`：保存追问/练习回答，再走同一套 Provider → Mastery Engine → Learning Policy 管道。

这些是协作边界，不要求前端等待最终数据库表名。表结构可以演进，但不能绕过事件历史和服务层。

## 6. GitHub 执行顺序

建议按依赖顺序领取，不要把所有页面同时做成互相猜测的假接口：

1. [#31 范围与数据/服务契约](https://github.com/njr070907/AI_SelfLearner/issues/31)
2. 后端 [#32 教学闭环](https://github.com/njr070907/AI_SelfLearner/issues/32) 与前端 [#33 学习页](https://github.com/njr070907/AI_SelfLearner/issues/33) 并行。
3. 后端 [#34 错题本服务](https://github.com/njr070907/AI_SelfLearner/issues/34) 完成后，前端做 [#35 错题本页面](https://github.com/njr070907/AI_SelfLearner/issues/35)。
4. 后端 [#36 复习调度](https://github.com/njr070907/AI_SelfLearner/issues/36) 完成后，前端做 [#37 复习页](https://github.com/njr070907/AI_SelfLearner/issues/37)。
5. 后端 [#38 长期状态与趋势](https://github.com/njr070907/AI_SelfLearner/issues/38)，前端同步接入进度展示。
6. 在 Fake 闭环稳定后，再继续现有的 [#24 Prompt v0.2 实验](https://github.com/njr070907/AI_SelfLearner/issues/24)、[#25 人工复核](https://github.com/njr070907/AI_SelfLearner/issues/25) 和 [#26 校准报告](https://github.com/njr070907/AI_SelfLearner/issues/26)。
7. 最后完成 [#39 完整集成与 7 天试用](https://github.com/njr070907/AI_SelfLearner/issues/39)。

## 7. MVP 停止条件

满足下面所有条件后，才把“完整自学系统 MVP”视为完成：

- 一个知识点可以完成教学、用户解释、追问/练习和诊断。
- 诊断证据能够生成错题/薄弱项，并在页面中查看。
- 到期复测可以完成，结果会确定性地改变下一次复习时间。
- 用户可以修正 AI 诊断，系统保留修正事件。
- 同一知识点可以看到当前状态、重复误区和基本趋势。
- Fake Provider 的端到端闭环、迁移、启动和关键回归测试通过。
- 固定模型 `deepseek-v4-flash-vision-exp` 完成小范围真实验证，并有人工语义复核记录。
- 至少完成一次 7 天小规模试用，记录真正阻塞学习的 UX 问题。

达到停止条件后，先评估用户是否真的获得了比普通聊天更好的诊断和复习体验，再决定是否投入 PDF/RAG、云端、多用户或移动端。

## 8. 风险与处理

| 风险 | 处理方式 |
| --- | --- |
| UI 很快完成但没有真实学习闭环 | 每个阶段都必须绑定后端验收，不以静态页面完成作为完成标准 |
| AI 语义波动 | 使用结构化 Schema、Fake 多场景、固定案例和人工复核；不直接改长期状态 |
| 前后端接口互相等待 | 先锁 typed contract，后端提供 Fake fixtures，前端并行开发 |
| 复习规则过早复杂化 | 先使用可解释的 1/3/7 天规则，所有间隔可配置 |
| 以后推翻协议导致数据作废 | 保存事件历史和原始证据，当前状态允许重算 |
| 真实调用成本失控 | 默认 Fake/dry-run；真实调用单案例、显式确认、零重试 |

## 9. 当前下一步

- 后端：开始 #38 长期状态、用户修正和趋势服务，复用教学、错题和复习事件历史。
- 前端协作者：领取 #33/#35/#37，接入学习、错题和复习页；先使用 Fake fixtures，不等待真实 AI。
- 产品负责人：在 #31 中确认“掌握/部分掌握/证据不足/误区”和反馈文案的可接受定义。

相关交接说明见 [`docs/collaboration/HANDOFF.md`](../collaboration/HANDOFF.md)，执行队列见 [`BACKLOG.md`](../../BACKLOG.md)。
