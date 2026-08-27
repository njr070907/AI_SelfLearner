# Backlog

本文件只记录当前可执行队列；完整产品需求见 `docs/28_AI_Growth_Companion_Backlog.md`。

## P0 — 当前里程碑

- [x] OpenAI Responses API 结构化输出适配器。
- [x] DeepSeek `deepseek-v4-flash-vision-exp` Chat Completions JSON Output 适配器。
- [x] 真实评测 CLI：显式 Provider、显式付费确认、默认 1 条、零重试。
- [x] Mock 覆盖成功、超时、限流/不可用、拒绝和无结构化输出。
- [x] 更新使用文档、环境变量示例和安全边界。
- [x] 运行 lint、format、mypy、tests、coverage、migration、启动和安全检查。
- [x] 提交、创建并合并 DeepSeek 适配器及修复/诊断 PR（#7–#15）。
- [x] 在固定模型 `deepseek-v4-flash-vision-exp` 下完成 1 条 strong 复核，自动检查通过。
- [x] 在固定模型下完成同一知识点 4 场景真实基线，自动检查 4/4 通过。
- [x] 在固定模型下完成完整 20 案例真实基线；20/20 结构成功，自动检查多轮达到最高 19/20。
- [x] 完成 GitHub 协作者交接包、按 `case_id` 的低成本评测入口和 Issue 模板（PR #23）。
- [x] 完成 Liquid Glass 学习工作区、主题/状态/展示层和 UI E2E 覆盖（PR #28）。
- [x] 完成 UI 动效、光效、导航指示器、下拉定位和深色主题对比度修复（PR #29）。

## P0 — 完整自学 MVP

这是当前从“工程底座”走向“用户可以正常使用的完整自学产品”的主队列。资料库 CRUD、资料到结构化导学的教学工作区、课程进度/报告和 20 条人工语义复核已完成；按最终用户验收重新校准的总进度约 **86.4%**，预计还需 **5–8 个有效工作日**，另需至少 7 个自然日试用；完整阶段、权重、时间估算、接口边界和停止条件见 [`docs/roadmap/FULL_SELF_STUDY_MVP_PLAN.md`](docs/roadmap/FULL_SELF_STUDY_MVP_PLAN.md) 和 [`docs/roadmap/MVP_PROGRESS.md`](docs/roadmap/MVP_PROGRESS.md)。

- [x] [#31](https://github.com/njr070907/AI_SelfLearner/issues/31) 锁定完整自学 MVP 范围与数据/服务契约。
- [x] [#32](https://github.com/njr070907/AI_SelfLearner/issues/32) 后端：实现完整教学闭环 API 与领域模型。
- [~] [#33](https://github.com/njr070907/AI_SelfLearner/issues/33) 前端：基础教学页面已完成；常规教学最终版仍在推进（学习入口、章节导航、互动进度和掌握检测分离）。
- [x] [#34](https://github.com/njr070907/AI_SelfLearner/issues/34) 后端：实现错题本数据模型与服务。
- [x] [#35](https://github.com/njr070907/AI_SelfLearner/issues/35) 前端：实现错题本页面（PR #59）。
- [x] [#36](https://github.com/njr070907/AI_SelfLearner/issues/36) 后端：实现复习调度与复测。
- [x] [#37](https://github.com/njr070907/AI_SelfLearner/issues/37) 前端：实现复习队列与复测页面（PR #59）。
- [x] [#38](https://github.com/njr070907/AI_SelfLearner/issues/38) 后端：实现反馈、长期状态与趋势。
- [ ] [#39](https://github.com/njr070907/AI_SelfLearner/issues/39) 集成教学、错题、复习、进度并完成 7 天试用（Fake 全链路已合并，连续试用与发布验收待完成）。
- [x] 本地资料库与教学来源：上传、查看、下载、重命名、替换、删除 PDF/Markdown/TXT；提取文字生成常规课程、互动小测并保存来源；掌握检测作为可选独立功能，不含 OCR/RAG。
- [x] 本轮教学进度基础：课程章节位置、互动答案、幂等请求和课程完成状态已持久化；当前全量回归 234 tests。
- [x] 资料库大文件默认处理：超过 20 MB 的 PDF 按页拆分，Markdown/TXT 按段落/行和安全字符边界拆分后自动导入；常见编码会保持可读文本，不静默替换字符。
- [x] 本地用户数据导出：生成带 manifest、Schema 版本、分表 JSON、资料文件和 SHA-256 校验的 ZIP；资料缺失时保留元数据并显式警告。
- [x] 课程报告后端化：统一计算课程完成数、互动题完成率、最新答题正确率和来源资料数；UI 不再自行拼接报告指标。
- [x] 文本资料安全提取：Markdown/TXT 无论大小均安全识别 UTF-8、UTF-16、GB18030 和 Big5，拒绝用替换字符静默损坏教学内容。
- [x] 后端主题自动选源：`TeachingService.recommend_sources()` 使用本地抽样和小型中英主题别名表推荐 PDF/Markdown/TXT 分卷，返回页码、分数、命中词、置信度和可审计 document IDs；不引入 RAG 或向量数据库。
- [x] PDF 视觉读取后端最小闭环：本地按主题选择最多 6 个页面并渲染为受限 JPEG；DeepSeek 教学 Provider 在显式视觉模式下发送图片内容块；文字路径、乱码拦截、结构/内容质量门槛和离线测试保持兼容；一次合成单页真实端点验证已成功。
- [x] 教学生成容错：视觉证据页码规范化与分卷换算、证据自动修复、`verified`/`repaired`/`partial`/`draft` 状态和 Provider 失败时的资料导读草稿保存；报告同步统计各状态课程。
- [ ] 前端接入主题自动选源：用户只填主题即可使用推荐分卷；中置信度显示确认和可增删分卷；低置信度要求手动选源；生成课程前展示最终来源范围。
- [ ] 常规教学最终验收：视觉/文字 Provider 生成内容必须与资料主题有实质相关性；深化跨课程学习报告、完成刷新后完整恢复和 7 天真实试用。

分工：当前 Codex 负责后端与学习核心；GitHub 合作者主要负责前端 UI；仓库所有者负责产品规则和最终验收。前端必须通过服务契约调用后端，不直接访问 SQL 或 Provider。

## P1 — 实验验证

- [x] 逐步扩展到 4 条场景覆盖；完整 20 条等待付费批准。
- [x] 保存模型、Prompt 哈希、Token 用量、延迟、请求 ID 与失败原因。
- [x] 汇总 Prompt v0.1 的首条误判：模型把未列出的 ε-δ 深入理解当作 gap；适配器已加入 coverage scope guard，保留 `evaluator-v0.1` 版本并等待下一轮受控验证。
- [ ] 根据稳定真实输出决定是否正式发布 Prompt v0.2。
- [x] [#24] 完成 Prompt v0.2 语义稳定性实验：固定模型、零重试、受控小样本/完整批量、误判分类和定向修复；仍不代表已发布。
- [x] [#25] 完成 20 条真实结果人工语义复核，记录自动结论与人工结论的差异。
- [x] [#26] 建立自动结果与人工结论的脱敏校准报告。
- [x] 生成 v0.2 AI 初审摘要：仅记录自动量表与场景形态检查，明确保留人工语义复核门槛。
- [x] 生成 v0.2 逐案例 AI 建议复核表，帮助负责人优先检查边界案例；不替代人工结论。
- [x] 根据产品负责人确认，将 Mastery Protocol 正式枚举更新为 `no_clue` / `re_learn`，并补充旧数据读取兼容与测试。
- [x] 根据人工复核反馈，将明确错误概念的默认动作从 `review` 校准为 `re_learn`，升级协议至 v0.4 并补充黄金集与策略测试。
- [x] 根据人工复核反馈，增加“明确自述忘记先 `review`，复习后低掌握再 `re_learn`”的分流规则，升级协议至 v0.5 并补充策略测试。
- [x] 根据人工复核反馈，将明确错误概念也纳入“先 `review`、复测后低掌握再 `re_learn`”分流，升级协议至 v0.6 并补充复习阶段策略测试。

## P1 — UI 验收

- [x] 在团队专用 `localhost:8511` 完成 Liquid Glass 工作区桌面 1440×1000、窄窗口 390×844、亮色/深色主题和主要交互的实际浏览器验收。
- [x] 将 UI 实际交互验收结论和契约限制记录到开发日志与 7 天试用准备清单。
