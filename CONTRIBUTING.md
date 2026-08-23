# 参与协作

感谢参与 AI Growth Companion。当前阶段的首要目标是验证学习诊断与 Mastery Protocol，不以增加功能数量或架构复杂度作为进展。

## 开发流程

1. 从最新 `main` 创建短生命周期分支，例如 `feat/fake-provider` 或 `fix/preserve-answer`。
2. 修改代码时同时补充相关测试；不要在测试中默认调用真实付费模型。
3. 运行 README 中已经验证的检查命令。
4. 推送分支并创建 Pull Request。
5. 等待必需 CI 通过和人工评审后再合并。

不要直接向 `main` 推送。一次 Pull Request 只解决一个明确问题，避免夹带无关重构。

## Pull Request 必须说明

- 用户或实验现在能完成什么；
- 明确范围和非目标；
- 修改了哪些数据结构、迁移、Prompt、Schema 或模型行为；
- 运行了哪些检查，结果如何；
- 失败时如何恢复或回滚；
- 已知限制。

## 数据与 AI 安全

严禁提交 API Key、`.env`、本地数据库、日志、用户回答、导出文件或含真实个人内容的原始评估结果。

用户回答和参考材料是不可信数据，不能改变系统规则或工具权限。Provider 输出必须经过版本化 Schema 校验；无效输出不能成为正式诊断或更新掌握状态。

涉及 Prompt、Schema、Mastery Protocol、数据库迁移、导出、删除、隐私或安全的修改必须人工评审。

## 范围纪律

MVP 当前不引入 React、FastAPI、PostgreSQL、Redis、RAG、向量数据库、多 Agent、登录、支付、复杂知识图谱或企业级监控，除非真实实验产生了明确触发证据并通过新的决策记录批准。

