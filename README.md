# AI Growth Companion

AI Growth Companion 是一个以费曼学习法为核心的学习诊断实验。用户用自己的话解释知识，系统基于证据指出理解缺口、可能误区和一个最小下一步。

当前阶段的目标不是构建完整 AI 伙伴，而是验证：AI 能否帮助用户发现“以为自己会、实际还没有真正理解”的部分。

## 当前状态

项目正在执行 Sprint 0：建立一个可在 GitHub 多人协作、可保存学习证据、可快速实验 Mastery Protocol 的可靠工程底座。

Sprint 0 使用 Fake Provider，不需要真实 API Key，也不声称已经具备真实学习诊断能力。

## 核心边界

```text
LLM Provider -> 提供结构化观察与证据
Mastery Engine -> 根据协议与历史判断当前状态
Learning Policy -> 决定一个最小下一步
```

LLM 是传感器，不是最终裁判。学习事件和原始证据会保留，当前掌握状态是可重新计算的派生结果。

## 文档入口

- [项目总上下文](docs/00_Project_Context_For_Codex.md)
- [最终主 PRD](docs/37_AI_Growth_Companion_Master_PRD.md)
- [Codex 启动指令](docs/38_Codex_Project_Kickoff_Instructions.md)
- [架构与数据流](docs/39_System_Architecture_and_Data_Flow.md)
- [测试与质量策略](docs/42_Test_and_Quality_Strategy.md)
- [隐私、安全与数据治理](docs/44_Privacy_Security_and_Data_Governance.md)
- [架构决策](docs/49_ADR_Architecture_Decision_Log.md)
- [完整文档索引](docs/51_Document_Index_and_Reading_Order.md)
- [Mastery Protocol](docs/mastery-protocol/README.md)

## 本地启动

实际安装、迁移、测试和启动命令将在 Sprint 0 工程骨架完成并从干净环境验证后补充。README 不提前记录未经验证的命令。

## 安全说明

不要提交 `.env`、API Key、本地数据库、日志、用户回答、数据导出或包含真实用户内容的原始评估结果。

当前产品不是正式考试、医疗、心理、法律、人格、智力或职业诊断工具。

## License

MVP 协作期暂不添加开源许可证，仓库默认保持私有。
