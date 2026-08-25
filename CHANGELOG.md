# 变更记录

本项目使用语义化版本管理应用版本；Prompt、Schema 和数据库迁移分别维护自己的版本。

## Unreleased

### 新增

- 建立 Python 3.12、uv 和 Streamlit 工程骨架。
- 实现 SQLite 顺序迁移、追加式学习事件历史和可重算当前状态。
- 实现结构化 Provider 协议及七种确定性 Fake 场景。
- 完成“知识点 → 回答 → Fake Provider → Schema → 保存 → 展示”端到端假闭环。
- 实现失败保留回答、幂等提交和使用同一回答重试。
- 增加 liveness、readiness 和 Provider dependency 健康检查。
- 增加单元、集成、Streamlit E2E、真实启动、Secret Scan、类型、覆盖率和依赖审计。
- 增加 GitHub Actions、Issue/PR 模板、协作规范和代码所有者。
- 增加 5 个高数知识点、四类回答矩阵组成的 20 个 Sprint 1 黄金案例草案。
- 增加黄金集严格 Schema、来源页码/哈希追溯、人工复核状态和 CI 校验。
- 完成 20 个黄金案例的逐项人工复核，并将 `high-math-mastery-v0.1` 标记为 `approved`。
- 明确机械复述只能支持 `fragile`，回答类型 `partial` 不自动等于掌握等级 `developing`。
- 增加独立版本与内容哈希的 `evaluator-v0.1` Prompt、输入边界和注入防护。
- 增加 20 案例 dry-run、Fake 批量运行器、版本化运行记录和付费调用安全门。
- 将确定性 Mastery Protocol 提升为 `mastery-protocol-v0.2-golden-baseline`，使部分复述映射为 `fragile`，并澄清观察置信度不是掌握分数。
- 增加 OpenAI Responses API 结构化输出适配器，并保持 Provider 只负责证据提取。
- 增加真实评测 CLI 安全门：显式付费确认、默认 1 条、零重试、输出 token 上限和本地运行记录。
- 增加真实 Provider 的全离线 Mock 测试，覆盖成功、超时、连接失败、限流、请求拒绝和结构化输出缺失。
- 增加 DeepSeek `deepseek-v4-flash-vision-exp` Chat Completions JSON Output 适配器，固定模型 ID 并在本地严格校验结果。
- 增加 DeepSeek 的 coverage scope guard、关闭思考模式、JSON 围栏/包裹文字恢复和零重试真实评测安全边界。
- 增加结构化失败分类、字段级安全诊断和 DeepSeek JSON 值类型约束；完成 4 场景真实基线。
- 完成 DeepSeek 指定模型完整 20 案例真实回归；20/20 结构成功，自动检查多轮最高 19/20，并记录语义稳定性限制。
- 增加 `evaluator-v0.2` 候选 Prompt、版本选择参数和零成本 dry-run；默认仍使用 `evaluator-v0.1`，不改变输出 Schema。
- 完成 Liquid Glass 学习工作区、主题/状态/展示层和 UI E2E 覆盖，并补充动效、光效、导航指示器、下拉定位和深色主题修复（PR #28、#29）。

### 数据与协议

- 数据库迁移版本：`1`。
- Fake Provider 模型标识：`fake-mastery-v0.1`。
- Provider 输出必须经过严格结构化 Schema 校验。
- Provider 仅提供观察，Mastery Engine 和 Learning Policy 分别负责判断与下一步。

### 验证

- 122 项自动测试通过。
- 分支覆盖率为 86%；DeepSeek 适配器本身为 81%。
- 数据库迁移、健康检查和真实 Streamlit 启动通过。
- Secret Scan、Ruff、Mypy 和依赖漏洞审计通过。
- GitHub Actions 的 Sprint 0 CI 已通过。

### 已知限制

- DeepSeek 完整 20 案例均能完成结构化调用，但自动语义检查在多轮运行中为 16–19/20；剩余问题进入 Prompt v0.2 稳定性实验，所有成功结果仍需人工复核。
- 当前只支持本地单用户 SQLite 数据。
- 私有仓库在现有 GitHub 套餐下无法启用分支保护，暂以 PR、CI 和协作约定保护 `main`。
- 尚未实现登录、同步、导出、删除、真实模型和正式部署。

### 回滚

- 应用代码可回滚到提交 `8418dac`，但不得删除已产生的学习事件。
- 数据库优先使用前向修复；当前没有破坏性回退迁移。
