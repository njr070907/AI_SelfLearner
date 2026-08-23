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

### 数据与协议

- 数据库迁移版本：`1`。
- Fake Provider 模型标识：`fake-mastery-v0.1`。
- Provider 输出必须经过严格结构化 Schema 校验。
- Provider 仅提供观察，Mastery Engine 和 Learning Policy 分别负责判断与下一步。

### 验证

- 38 项自动测试通过。
- 分支覆盖率为 88%。
- 数据库迁移、健康检查和真实 Streamlit 启动通过。
- Secret Scan、Ruff、Mypy 和依赖漏洞审计通过。
- GitHub Actions 的 Sprint 0 CI 已通过。

### 已知限制

- 当前只实现 Fake Provider，不能产生真实学习诊断。
- 当前只支持本地单用户 SQLite 数据。
- 私有仓库在现有 GitHub 套餐下无法启用分支保护，暂以 PR、CI 和协作约定保护 `main`。
- 尚未实现登录、同步、导出、删除、真实模型和正式部署。

### 回滚

- 应用代码可回滚到提交 `8418dac`，但不得删除已产生的学习事件。
- 数据库优先使用前向修复；当前没有破坏性回退迁移。
