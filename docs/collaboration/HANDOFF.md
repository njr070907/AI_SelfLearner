# GitHub 协作者交接手册

这份手册是当前阶段的“从哪里开始”说明。它服务于 Sprint 1 的 Mastery Protocol 实验，不要求新协作者重新阅读全部历史聊天记录。

## 当前基线（2026-08-26）

- `main` 已通过必需 CI，工程链路包括启动、迁移、Fake Provider、严格 Schema、事件历史、Mastery Engine、Learning Policy、端到端假闭环、资料库 CRUD、资料生成导学和第一版 Liquid Glass 学习工作区 UI。
- 评测集包含 20 个高等数学案例。v0.2 主运行 `020209Z` 为 18/20 结构成功、18/18 自动通过；两条定向复测 `020421Z` 均通过，合并后的 20 条结果为 20/20 自动量表通过。
- 20 条 v0.2 真实结果已逐条完成人工语义复核。当前结论是：接口和数据管道稳定，旧 Prompt/枚举结果存在历史差异，不能把自动通过数单独当作掌握度结论。
- 真实 Provider 必须使用 `deepseek-v4-flash-vision-exp`。没有新的实验设计前，不要盲目重复完整付费运行。
- UI v1 已在 PR #28–#29 合并，Prompt v0.2 候选版本在 PR #30 合并；PR #58/#59 已合并教学、错题本、复习复测、反馈/长期状态进度页、Fake 全链路和资料库基础版；当前协作分支又补齐“上传资料→生成常规课程→阅读→互动小测→保存/恢复进度→课程报告”，掌握检测为可选独立功能，离线回归为 211 个测试通过；课程报告指标已由 `TeachingService.get_learning_report()` 统一提供，系统页已接入本地导出下载；两个受控真实 DeepSeek 教学案例已完成人工语义复核并通过；资料库大文件自动分卷已接入，新增和替换入口统一按同一规则处理。
- 完整自学 MVP 按最终用户可正常使用的验收口径当前约完成 86%，预计还需 5–8 个有效工作日（含验证和发布准备），另需至少 7 个自然日试用；20 条真实语义人工验收已完成，剩余重点是来源内容质量人工验收、报告深化、发布边界确认和 7 天试用闭环。本地用户数据导出已提供 CLI，不含网络上传。
- Mastery Protocol 已升级为 v0.6：`no_clue`=完全未掌握，`re_learn`=重新学习；明确错误概念和自述忘记都先进入 `review`，复测后低掌握再进入 `re_learn`。20 条 v0.2 结果已按新协议复核并归档，不能直接把旧枚举当作发布结论。
- 完整阶段、时间估算、停止条件和前后端边界见 [完整自学 MVP 开发计划](../roadmap/FULL_SELF_STUDY_MVP_PLAN.md)。

## 谁负责什么

| 角色 | 责任 |
| --- | --- |
| 产品/协议负责人（仓库所有者） | 定义“掌握”的产品标准，确认人工复核结论，批准 Prompt/Schema/协议方向，验收学习体验 |
| 当前 Codex（后端/学习核心） | 负责数据模型、迁移、事件历史、Mastery Engine、Learning Policy、Provider、服务契约、测试和 CI |
| GitHub 合作者（前端 UI） | 负责 Streamlit 页面、组件、交互、主题/响应式、加载/空/错误状态和 UI 验收；使用服务契约，不直接写 SQL 或业务规则 |
| 独立复核者 | 检查数学语义、证据是否足够、是否把模型输出误当最终裁判 |
| CI | 自动检查密钥、格式、lint、测试、迁移和启动；CI 通过不等于语义实验通过 |

前后端以 typed service models 协作。后端先提供 Fake fixtures，前端可以无 API Key 并行开发；需要增加字段时，先改服务契约和测试，再改页面。Provider 只是证据传感器，长期状态只能由 Mastery Engine 和 Learning Policy 计算。完整分阶段计划见 [完整自学 MVP 开发计划](../roadmap/FULL_SELF_STUDY_MVP_PLAN.md)。

前端页面可优先调用 `LearningService.get_workspace_snapshot()` 获取一致的 `history`、`concept_states`、`wrong_items` 和 `review_queue`；它只负责组合后端结果，不应在 UI 中重新计算掌握等级、错误分类或复习间隔。

## 新成员首次操作

```powershell
git clone https://github.com/njr070907/AI_SelfLearner.git
cd AI_SelfLearner
uv sync --locked --all-groups
uv run python -m ai_growth_companion.repositories.database migrate
uv run python -m ai_growth_companion.application.health
uv run pytest
uv run python scripts/seed_fake_workspace.py --seed-name frontend-demo
uv run python scripts/run_golden_eval.py --dry-run
```

如果只想验证一个案例：

```powershell
uv run python scripts/run_golden_eval.py --provider fake --case-id hm-lhopital-strong --dry-run
```

`--case-id` 可以重复使用；不能和 `--max-cases` 一起用。案例列表在 `evals/golden/cases.json`。

## 领取和完成一个工作项

1. 从最新 `main` 创建短分支：`feat/<issue>-short-name`、`fix/<issue>-short-name` 或 `experiment/<issue>-prompt-v02`。
2. 在 Issue 中写清假设、案例范围、预期指标、非目标和停止条件。
3. 代码变更必须配套测试；Prompt、Schema、Mastery Protocol 和迁移变更必须同步文档。
4. 先用 Fake 或 `--dry-run` 验证，再决定是否需要真实模型调用。
5. 提交 PR，关联 Issue，填写 PR 模板，等待 CI 和人工复核。
6. 只在 PR 合并后删除分支；不要直接推送 `main`、强推共享历史或提交密钥。

## 真实模型调用安全边界

真实调用会产生费用，也会受到供应商配额影响。必须满足以下规则：

- Provider 固定选择 `deepseek`，模型固定为 `deepseek-v4-flash-vision-exp`。
- API Key 只放在本机 `.env`，不进入 Issue、PR、日志或提交。
- 命令必须显式带 `--confirm-paid-calls`；第一次只跑一个明确的 `--case-id`。
- 默认零重试；不要为了让数字好看而重复运行。
- 运行记录保留在本地 `evals/runs/`，上传 GitHub 时只提交脱敏摘要。
- 自动 Schema 通过只说明“结构可消费”，最终语义结论必须由人工复核确认。

示例（确认费用后才能执行）：

```powershell
uv run python scripts/run_golden_eval.py `
  --provider deepseek `
  --case-id hm-lhopital-strong `
  --confirm-paid-calls
```

## 当前优先工作

1. 查阅 [v0.2 人工复核结果](../mastery-protocol/V0_2_REVIEW_DRAFT.md) 和 [校准报告](../mastery-protocol/REAL_SEMANTIC_CALIBRATION.md)；20 条语义确认已完成，继续保持 v0.2 为候选版本，直到发布边界决定完成。
2. 使用 `docs/roadmap/SEVEN_DAY_TRIAL_READINESS.md` 的固定 Fake 环境完成进入试用前的最终检查，并开始记录真实 7 个自然日。
3. 完成 #39 的连续试用、发布检查和最终产品验收；不要把 Fake 测试结果当作真实模型质量结论。

### 本地数据导出

```powershell
uv run python scripts/export_user_data.py
```

导出文件写入被 Git 忽略的 `exports/`，不要把用户导出包提交到仓库。

### 前端本地演示数据

如果需要一次性看到学习记录、知识状态、错题和到期复习项目，可以运行：

```powershell
uv run python scripts/seed_fake_workspace.py --seed-name frontend-demo
```

命令只使用 Fake Provider，不访问网络、不产生费用，也不删除已有数据。同一个 `--seed-name` 可以重复运行而不会重复创建记录；换一个名称会创建另一批演示数据。默认写入当前 `DATABASE_URL` 指向的 SQLite 数据库。

## 验收标准

- 相关单元、集成或 E2E 测试通过；Ruff、格式检查和 Mypy（若触及类型）通过。
- 真实实验有可重复的案例范围、Prompt 版本、模型名、运行 ID 和脱敏摘要。
- Provider 仍只是证据传感器；Mastery Engine 和 Learning Policy 的确定性规则没有被模型输出绕过。
- 没有提交 API Key、`.env`、数据库、用户原文或原始真实评测输出。
- `CURRENT.md`、`BACKLOG.md`、`BLOCKED.md` 或 `DEVELOPMENT_LOG.md` 在需要时同步更新。

## 重要入口

- [当前状态](../../CURRENT.md)
- [待办队列](../../BACKLOG.md)
- [阻塞项](../../BLOCKED.md)
- [开发日志](../../DEVELOPMENT_LOG.md)
- [架构决策](../../DECISIONS.md)
- [评测说明](../../evals/README.md)
- [Mastery Protocol](../mastery-protocol/README.md)
- [完整自学 MVP 开发计划](../roadmap/FULL_SELF_STUDY_MVP_PLAN.md)
- [MVP 进度面板](../roadmap/MVP_PROGRESS.md)
- [GitHub MVP Issues #31–#39](https://github.com/njr070907/AI_SelfLearner/issues?q=is%3Aissue+label%3Aenhancement)

## 恢复位置

如果中断，先运行 `git status`，阅读 `CURRENT.md` 和本手册，再从“当前优先工作”的第一个未关闭 Issue 开始。不要直接从旧的聊天上下文恢复付费调用。
