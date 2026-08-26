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

这是当前从“工程底座”走向“用户可以正常使用的完整自学产品”的主队列。PR #59 已合并后，按最终用户验收重新校准的总进度约 **89%**，预计还需 **5–10 个有效工作日**，另需至少 7 个自然日试用；完整阶段、权重、时间估算、接口边界和停止条件见 [`docs/roadmap/FULL_SELF_STUDY_MVP_PLAN.md`](docs/roadmap/FULL_SELF_STUDY_MVP_PLAN.md) 和 [`docs/roadmap/MVP_PROGRESS.md`](docs/roadmap/MVP_PROGRESS.md)。

- [x] [#31](https://github.com/njr070907/AI_SelfLearner/issues/31) 锁定完整自学 MVP 范围与数据/服务契约。
- [x] [#32](https://github.com/njr070907/AI_SelfLearner/issues/32) 后端：实现完整教学闭环 API 与领域模型。
- [x] [#33](https://github.com/njr070907/AI_SelfLearner/issues/33) 前端：实现学习教学流程页面（PR #58）。
- [x] [#34](https://github.com/njr070907/AI_SelfLearner/issues/34) 后端：实现错题本数据模型与服务。
- [x] [#35](https://github.com/njr070907/AI_SelfLearner/issues/35) 前端：实现错题本页面（PR #59）。
- [x] [#36](https://github.com/njr070907/AI_SelfLearner/issues/36) 后端：实现复习调度与复测。
- [x] [#37](https://github.com/njr070907/AI_SelfLearner/issues/37) 前端：实现复习队列与复测页面（PR #59）。
- [x] [#38](https://github.com/njr070907/AI_SelfLearner/issues/38) 后端：实现反馈、长期状态与趋势。
- [ ] [#39](https://github.com/njr070907/AI_SelfLearner/issues/39) 集成教学、错题、复习、进度并完成 7 天试用（Fake 全链路已合并，连续试用与发布验收待完成）。

分工：当前 Codex 负责后端与学习核心；GitHub 合作者主要负责前端 UI；仓库所有者负责产品规则和最终验收。前端必须通过服务契约调用后端，不直接访问 SQL 或 Provider。

## P1 — 实验验证

- [x] 逐步扩展到 4 条场景覆盖；完整 20 条等待付费批准。
- [x] 保存模型、Prompt 哈希、Token 用量、延迟、请求 ID 与失败原因。
- [x] 汇总 Prompt v0.1 的首条误判：模型把未列出的 ε-δ 深入理解当作 gap；适配器已加入 coverage scope guard，保留 `evaluator-v0.1` 版本并等待下一轮受控验证。
- [ ] 根据稳定真实输出决定是否正式发布 Prompt v0.2。
- [ ] [#24] 设计 Prompt v0.2 语义稳定性实验：固定采样/重复运行、误判分类、人工复核和是否需要确定性校准。
- [ ] [#25] 完成 20 条真实结果人工语义复核，记录自动结论与人工结论的差异。
- [ ] [#26] 建立自动结果与人工结论的脱敏校准报告。

## P1 — UI 验收

- [x] 在团队专用 `localhost:8511` 完成 Liquid Glass 工作区桌面 1440×1000、窄窗口 390×844、亮色/深色主题和主要交互的实际浏览器验收。
- [x] 将 UI 实际交互验收结论和契约限制记录到开发日志与 7 天试用准备清单。
