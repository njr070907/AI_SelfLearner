# 项目 README 基线

仓库根目录的 [`README.md`](../README.md) 是当前可执行的项目入口，已经包含经过验证的安装、迁移、健康检查、测试和启动命令。本文件只保留文档基线与维护规则，避免两份快速开始长期漂移。

## 当前状态

Sprint 0 工程基线已经完成：Streamlit、SQLite migration、多场景 Fake Provider、结构化 Schema、学习事件历史、可重算当前状态、端到端假闭环和分级 CI 均已实现并验证。

这不代表真实学习诊断已经完成。当前 Provider 结果全部是免费、确定性的测试数据；Sprint 1 才开始验证真实 Mastery Protocol。

## 最短启动路径

```powershell
uv sync --locked --all-groups
uv run python -m ai_growth_companion.repositories.database migrate
uv run python -m ai_growth_companion.application.health
uv run streamlit run app.py
```

完整克隆、配置、检查和协作命令以根目录 [`README.md`](../README.md) 为准。

## README 维护规则

- 命令必须在实际工程中验证后才能写入。
- 用户可见行为、安装步骤、配置项或已知限制变化时，同一个 Pull Request 必须更新根 README。
- 不在 README 中宣称尚未实现的真实 AI、部署、登录、同步、导出或删除能力。
- 重大协议、架构和数据变化分别更新 Mastery Protocol、ADR 和变更记录。
- 仓库公开或接受外部贡献前，必须明确许可证和贡献条款。

## 文档入口

- [最终主 PRD](37_AI_Growth_Companion_Master_PRD.md)
- [Codex 启动指令](38_Codex_Project_Kickoff_Instructions.md)
- [架构与数据流](39_System_Architecture_and_Data_Flow.md)
- [测试与质量策略](42_Test_and_Quality_Strategy.md)
- [隐私与安全](44_Privacy_Security_and_Data_Governance.md)
- [发布与回滚](48_Release_CI_CD_and_Rollback.md)
- [架构决策](49_ADR_Architecture_Decision_Log.md)
- [完整文档索引](51_Document_Index_and_Reading_Order.md)
- [Mastery Protocol](mastery-protocol/README.md)
