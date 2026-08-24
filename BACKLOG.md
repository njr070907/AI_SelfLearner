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

## P1 — 实验验证

- [x] 逐步扩展到 4 条场景覆盖；完整 20 条等待付费批准。
- [x] 保存模型、Prompt 哈希、Token 用量、延迟、请求 ID 与失败原因。
- [x] 汇总 Prompt v0.1 的首条误判：模型把未列出的 ε-δ 深入理解当作 gap；适配器已加入 coverage scope guard，保留 `evaluator-v0.1` 版本并等待下一轮受控验证。
- [ ] 根据稳定真实输出决定是否正式发布 Prompt v0.2。
- [ ] 设计 Prompt v0.2 语义稳定性实验：固定采样/重复运行、误判分类、人工复核和是否需要确定性校准。
