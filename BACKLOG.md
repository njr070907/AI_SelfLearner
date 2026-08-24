# Backlog

本文件只记录当前可执行队列；完整产品需求见 `docs/28_AI_Growth_Companion_Backlog.md`。

## P0 — 当前里程碑

- [x] OpenAI Responses API 结构化输出适配器。
- [x] DeepSeek `deepseek-v4-flash-vision-exp` Chat Completions JSON Output 适配器。
- [x] 真实评测 CLI：显式 Provider、显式付费确认、默认 1 条、零重试。
- [x] Mock 覆盖成功、超时、限流/不可用、拒绝和无结构化输出。
- [x] 更新使用文档、环境变量示例和安全边界。
- [x] 运行 lint、format、mypy、tests、coverage、migration、启动和安全检查。
- [x] 提交、创建并合并 PR #4。
- [ ] 获得 API Key 与费用授权后，先跑 1 条真实案例并人工复核。

## P1 — 实验验证

- [ ] 逐步扩展到 4 条场景覆盖，再扩展到完整 20 条。
- [ ] 保存模型、Prompt 哈希、Token 用量、延迟、请求 ID 与失败原因。
- [ ] 汇总 Prompt v0.1 的误判模式，决定是否进入 Prompt v0.2。
