# 7 天试用准备清单

> 状态：PR #59 已合并，候选版本已通过进入试用前的工程验收。这里记录的是 **Ready for 7-day trial** 的进入条件，
> 不是已经完成 7 个自然日试用的证明。

## 进入试用前的产品门槛

- [x] 学习：创建会话、回答、结构化诊断、重新解释、追问和失败重试。
- [x] 错题：列表、筛选、排序、证据详情、标记掌握、安排复习和重新作答。
- [x] 复习：到期队列、复测、反馈、下一题、失败保留回答和后端重新安排。
- [x] 进度：展示后端长期状态、趋势、错题、复测和用户修正统计。
- [x] Fake Provider 默认开启，演示数据脚本保持零网络、零付费调用。
- [x] Streamlit AppTest 覆盖完整 Fake 自学闭环和刷新后的持久化状态。
- [x] `localhost:8511` Desktop（1440 × 1000）实际浏览器验收通过，无横向溢出。
- [x] `localhost:8511` Narrow（390 × 844）实际浏览器验收通过，移动侧栏和深色控件可用且无横向溢出。
- [x] 仓库完整回归通过：228 tests、Ruff、format、mypy、Streamlit smoke、Secret Scan、黄金集校验、Prompt dry-run 和依赖审计。
- [x] DeepSeek `deepseek-v4-flash-vision-exp` v0.2 20 条真实结果已完成逐条人工语义复核，并按 Mastery Protocol v0.6 归档差异。
- [x] [PR #59](https://github.com/njr070907/AI_SelfLearner/pull/59) 已合并，#35/#37 已完成，#39 进入连续试用与发布验收阶段。

## 2026-08-26 试用前预检

- 使用隔离数据库 `tmp/trial-preflight.db` 完成迁移：当时版本 `0 -> 5`，5 个迁移全部成功；后续新增教学进度迁移至 7，因此开始正式试用前必须在新的隔离库再次执行迁移预检。
- 使用 `preflight-check` 种子生成演示工作区：4 条历史、3 个知识状态、3 个错题、3 个到期复习项目；未删除已有数据，网络调用 0，付费调用 0。
- 应用健康检查：旧预检中的 liveness、readiness、Fake Provider 均为 `healthy`，数据库版本 5/5；当前代码要求正式试用前确认数据库版本 7/7。
- `evaluator-v0.2` dry-run：20 个 Prompt envelope 全部渲染成功，Provider 调用 0，预计费用 `$0`。
- 协议 v0.6 预检：Fake 全量评测 20/20 自动通过，正式输出包含 `no_clue/re_learn`，错误概念和自述忘记先进入 `review`，复习后低掌握再进入 `re_learn`；旧 v0.2 数据库继续可读并可追加新记录。
- 该预检证明 Fake 试用环境可以启动，不代表真实 DeepSeek 语义已经通过，也不计入 7 个自然日。

## 2026-08-26 当前分支预检

- 新建隔离数据库 `tmp/current-preflight.db`，迁移 `0 -> 7`、7 个迁移全部成功，状态命令确认 `7/7`。
- 当前分支 Fake 种子生成 4 条历史、3 个知识状态、3 个错题和 3 个到期复习项目；重复执行保持幂等，网络调用 0、付费调用 0。
- 健康检查 liveness、readiness、Fake Provider 均为 `healthy`；这次预检仍不计入真实 7 个自然日。

## 2026-08-26 发布前再次预检

- 新建隔离数据库 `tmp/release-preflight-20260826-2.db`，迁移 `0 -> 7`，7 个迁移全部成功。
- Fake 种子生成 4 条历史、3 个知识状态、3 个错题和 3 个到期复习项目；使用稳定种子名，重复执行保持幂等，不删除已有数据。
- 健康检查 liveness、readiness、Fake Provider 均为 `healthy`，数据库版本确认 `7/7`。
- `scripts/smoke_streamlit.py` 实际启动 Streamlit 并返回 HTTP 200；本次没有网络调用和付费调用。
- 两个受控真实 DeepSeek 教学案例已经完成人工语义复核并通过，但仍不计入 7 个自然日连续试用。

## 2026-08-26 发布候选自动审计

- Secret Scan：180 个仓库文件通过。
- Streamlit smoke：通过（隔离端口 `64100`）。
- 依赖审计：未发现已知漏洞；本地项目包因不发布到 PyPI 被工具跳过，属于预期结果。
- 隔离数据库发布预检：早期记录为迁移 `0 -> 5`；当前分支已再次确认迁移 `0 -> 7`、Fake 种子、健康检查和 Streamlit smoke 均通过；网络调用 0、付费调用 0。
- 尚未完成且不能由自动检查替代：真实备份/恢复与回滚演练、产品负责人发布边界决定、真实 7 个自然日连续试用。

## 固定试用环境

团队验收环境只使用 `8511`，不复用或停止个人版本的 `8501`：

```powershell
$env:DATABASE_URL = "sqlite:///data/team-8511.db"
$env:LLM_PROVIDER = "fake"
$env:LLM_MODEL = "fake-mastery-v0.1"
$env:LLM_PAID_CALLS_ALLOWED = "false"
uv run python -m ai_growth_companion.repositories.database migrate
uv run python scripts/seed_fake_workspace.py --seed-name frontend-demo
uv run streamlit run app.py --server.port 8511
```

团队试用环境可按上述命令在 `localhost:8511` 启动并通过 HTTP 200 检查；旧环境数据库可能仍停留在迁移 5，正式试用前需先执行迁移并确认当前版本为 7。环境启动本身不计入 Day 1，只有试用者实际完成学习闭环后才填写每日记录。

## 每日试用记录（不得预填）

实际试用开始后，每个自然日由试用者填写；空白表示尚未发生，不得用 Fake 数据代替：

| 自然日 | 日期 | 学习主题 | 完成闭环 | 失败恢复 | 最有价值反馈 | 主要问题 | 是否愿意次日继续 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Day 1 |  |  |  |  |  |  |  |
| Day 2 |  |  |  |  |  |  |  |
| Day 3 |  |  |  |  |  |  |  |
| Day 4 |  |  |  |  |  |  |  |
| Day 5 |  |  |  |  |  |  |  |
| Day 6 |  |  |  |  |  |  |  |
| Day 7 |  |  |  |  |  |  |  |

完成真实 7 天后再汇总：持续使用意愿、诊断帮助程度、发现的真实误判、恢复失败、
复习节奏问题和下一阶段决策。在此之前只能写“准备进入试用”。

## 真实 DeepSeek 验证边界

当前真实模型路径已具备三重显式门槛：指定 `deepseek`、固定模型
`deepseek-v4-flash-vision-exp`、明确允许付费调用。默认应用和所有自动化测试仍使用 Fake。

付费验证只能在用户再次明确授权、合法本机配置已存在时，按照
[`README.md`](../../README.md#deepseek-真实评测会产生费用) 的单案例、零重试步骤执行。
本轮没有修改 Key、`.env`、Provider Factory 或真实模型默认配置，也没有发起真实调用。

## 已知契约限制

- 正式服务契约目前没有“手动延后复习”或“任意指定下一次日期”的方法。UI 会展示禁用入口和原因，
  不直接写数据库，也不自行计算调度日期。
- “重新安排”展示 `submit_retest(...)` 返回的后端日期和间隔；这不是前端推算。
- 一次真实模型验证不能替代 7 个自然日的连续试用，也不能单独证明诊断质量。
