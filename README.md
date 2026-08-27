# AI Growth Companion

AI Growth Companion 是一个以常规课程学习为主、以费曼式主动表达诊断为差异化能力的自学系统。用户先阅读 AI 根据资料整理的课程，再通过互动练习和可选掌握检测确认理解；系统保存学习证据、指出理解缺口和可能误区，并给出一个最小下一步。

项目当前已经完成 Sprint 0 工程基线。仓库默认使用免费、可预测的 Fake Provider，用于验证产品管道，不代表真实 AI 学习判断；本机也可以选择 Ollama 本地模型进行开发验证。

Sprint 1 已开始建立 Mastery Protocol 的真实评测基线。第一批 20 个高等数学案例已经由产品负责人逐项完成人工复核，可以作为第一版回归基线；在真实模型实验通过前，项目仍不会声称能够可靠诊断学习掌握度。

`evaluator-v0.1` 已作为独立、可哈希的 Prompt 版本加入工程；`evaluator-v0.2` 现作为候选实验版本提供，但默认不会启用。运行器支持零调用 dry-run、免费确定性的 Fake 管道基线和默认关闭的 DeepSeek 适配器；付费真实 Provider 只有在明确选择供应商、Prompt 版本、模型并确认付费后才会启用，Ollama 本地模式不受此付费门槛影响。

## Sprint 0 已经能做什么

- 启动 Streamlit 页面，创建知识点学习会话并保存回答。
- 用七种确定性 Fake 场景模拟充分理解、部分正确、误区、证据不足和 Provider 故障。
- 通过严格 Schema 校验 Provider 输出，格式错误不会进入正式诊断。
- 将原始回答、诊断尝试和学习事件保存到 SQLite。
- 保存追加式 Event History，并将 Current State 作为可重新计算的投影。
- Provider 失败时保留用户回答，并可使用同一回答重试。
- 资料库支持上传、查看、下载、重命名、替换和删除 PDF、Markdown、TXT 文件；超过 20 MB 的文件会默认自动分卷后导入：PDF 按页、Markdown/TXT 按段落和行尾优先，原文内容不改写；教学提取会保留页面/片段级 source units，长文本安全识别常见编码并按主题选取相关上下文。在“教学”页选择资料后，可由 Fake、Ollama 本地文本模型或固定 DeepSeek Provider 生成可阅读的结构化导学；真实 Provider 若输出缩略 JSON，会触发一次受限结构补全和 evidence-only 修复，不能绕过原文证据校验。对扫描版、乱码或公式较多的 PDF，教学页还提供显式的“使用视觉读取 PDF 页面”模式：本地只渲染最多 6 个相关页面为受限 JPEG，再以图片内容块发送给视觉 Provider；默认仍不发送图片、不产生付费调用。
- “学习”入口默认进入常规教学：按章节阅读、上一节/下一节、完成末节互动小测；章节位置、互动答案和课程完成状态会保存，掌握检测单独作为可选入口。
- 运行数据库迁移、健康检查、自动测试、Secret Scan 和真实启动冒烟测试。
- 在 GitHub Actions 中执行阻断检查和非阻断质量报告。

现在的自学闭环如下：

```text
资料库上传 → 本地提取文字（必要时视觉读取 PDF 页面） → AI 生成教学导学 → 章节阅读
       → 互动小测 → 保存课程进度 → 可选掌握检测
       → 用户回答 → Fake/Ollama/DeepSeek Provider → Schema 校验
       → 保存学习证据 → Mastery Engine → Learning Policy → 页面展示
```

教学导学包含摘要、学习目标、概念、机制、适用边界、例子、检查问题和来源文件。扫描版 PDF 默认仍提示先 OCR；如果用户显式开启视觉模式，系统会将有限页面渲染为图片并要求 Provider 读取原图。当前不做整本 PDF 图片上传、OCR 服务、RAG 或向量数据库。

其中：

```text
Provider        → 提供结构化观察与证据
Mastery Engine  → 根据协议与历史判断当前状态
Learning Policy → 决定一个最小下一步
```

Provider 是传感器，不是最终裁判。

## 本地启动

需要提前安装 Git、[uv](https://docs.astral.sh/uv/) 和可用的网络连接。Python 3.12 会由 uv 按项目声明安装或选择。

```powershell
git clone https://github.com/njr070907/AI_SelfLearner.git
cd AI_SelfLearner
uv sync --locked --all-groups
uv run python -m ai_growth_companion.repositories.database migrate
uv run python -m ai_growth_companion.application.health
uv run streamlit run app.py
```

浏览器通常会自动打开 `http://localhost:8501`。Sprint 0 默认配置可以直接运行，不需要创建 `.env`，也不需要 API Key。

导出当前本地用户的数据（学习事件、诊断、错题、复习、课程进度和资料文件）到被 Git 忽略的 `exports/`：

```powershell
uv run python scripts/export_user_data.py
```

导出包是自描述 ZIP，包含 `manifest.json`、分表 JSON、资料文件和 SHA-256 校验值；如果资料文件已从磁盘丢失，导出仍会保留元数据并在清单中明确警告。

如需修改本地配置，可先复制示例文件：

```powershell
Copy-Item .env.example .env
```

macOS 或 Linux 使用：

```bash
cp .env.example .env
```

## 运行检查

提交代码前至少运行：

```powershell
uv run python scripts/scan_secrets.py
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python scripts/smoke_streamlit.py
uv run python scripts/run_golden_eval.py --dry-run
uv run python scripts/run_golden_eval.py
```

完整质量报告：

```powershell
uv run mypy src app.py scripts
uv run pytest --cov --cov-report=term-missing
uv run pip-audit
```

CI 中必须通过的项目包括 Secret Scan、基础 lint、格式、数据库迁移、全部测试和真实 Streamlit 启动。类型、覆盖率和依赖审计当前提供非阻断报告，避免工程质量指标阻塞产品验证。

## Fake Provider 场景

| 场景 | 用途 |
| --- | --- |
| `strong` | 模拟回答充分、证据较强 |
| `partial` | 模拟部分正确但有缺口 |
| `misconception` | 模拟回答中存在错误概念 |
| `insufficient_evidence` | 模拟证据不足，需要继续追问 |
| `provider_timeout` | 模拟 Provider 超时 |
| `provider_failure` | 模拟 Provider 服务失败 |
| `invalid_schema` | 模拟输出格式不符合协议 |

这些场景都是免费的固定测试数据，不会访问外部模型。

## Prompt 与批量评测

只验证 Prompt 渲染、输入边界和 20 个案例数量，不调用 Provider：

```powershell
uv run python scripts/run_golden_eval.py --dry-run
```

验证 Prompt v0.2 候选版本（仍然零调用）：

```powershell
uv run python scripts/run_golden_eval.py `
  --prompt-version v0.2 `
  --case-id hm-lhopital-strong `
  --dry-run
```

默认仍使用 `v0.1`。Prompt v0.2 只改变证据观察指令，继续输出 `provider-observation-v0.1`，并通过运行记录保存版本和哈希。在 Prompt v0.2 完成小范围对照实验前，不要直接扩大真实付费批量。

运行确定性的 Fake 管道基线：

```powershell
uv run python scripts/run_golden_eval.py
```

只复现指定的一个或几个案例（不会重新跑完整 20 条）：

```powershell
uv run python scripts/run_golden_eval.py --dry-run --case-id hm-lhopital-strong
uv run python scripts/run_golden_eval.py --provider fake `
  --case-id hm-lhopital-strong `
  --case-id hm-definite-integral-partial
```

`--case-id` 可以重复使用，顺序就是实际运行顺序；它与 `--max-cases` 不能同时使用。案例编号和人工复核说明见
[`evals/golden/cases.json`](evals/golden/cases.json) 与 [`evals/README.md`](evals/README.md)。

结果写入被 Git 忽略的 `evals/runs/`。Fake 基线通过只表示 Schema、Mastery Engine、Learning Policy 和自动检查互相一致；每条成功结果仍标记为需要人工语义复核，不能作为真实模型质量结论。DeepSeek 等付费真实 Provider 模式必须显式允许付费调用；Ollama 本地模式不产生供应商费用。所有模式默认零重试，避免意外扩大成本。

### DeepSeek 真实评测（会产生费用）

适配器使用 DeepSeek 的 OpenAI 兼容 Chat Completions JSON Output，随后在本地用 Pydantic 严格校验 `ProviderObservation`；掌握状态和下一步仍由本地确定性代码决定。接口依据见 [DeepSeek JSON Output 官方文档](https://api-docs.deepseek.com/guides/json_mode/) 和 [DeepSeek 首次 API 调用文档](https://api-docs.deepseek.com/guides/function_calling)。

先将 `.env.example` 复制为被 Git 忽略的 `.env`，再只在本机填写：

```dotenv
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-v4-flash-vision-exp
LLM_API_KEY=<本机 API Key>
LLM_PAID_CALLS_ALLOWED=true
```

应用启动时也会读取这三个条件：只有 Provider 为 `deepseek`、模型完全匹配且显式打开 `LLM_PAID_CALLS_ALLOWED=true`，交互式学习服务才会构造真实 Provider；默认 Fake 模式不会访问外部网络。真实模式仍然零自动重试，题目生成暂由本地 Fake 提供，DeepSeek 只负责结构化证据提取。

完成费用授权后，首次只运行 1 条：

```powershell
uv run python scripts/run_golden_eval.py `
  --provider deepseek `
  --case-id hm-lhopital-strong `
  --confirm-paid-calls
```

真实模式默认 `--max-cases 1`、每条零重试、最多输出 1200 tokens。只有显式传入 `--max-cases 2` 至 `20` 才会扩大批量。Token 用量、延迟、模型、Prompt 版本、请求 ID 和错误码会写入本地运行记录；API Key、Prompt 原文和回答原文不会进入控制台摘要。实际账单以供应商后台为准，运行器目前不猜测费用。

即使自动检查全过，仍必须逐条人工复核数学语义；一次真实运行不直接更新学习者长期状态。

### 本地 Ollama 三模型路由（开发和日常使用）

本地模式不需要 API Key，也不会把文字资料发送到外部服务。应用按任务选择模型：

| 任务 | 默认模型 | 职责 |
| --- | --- | --- |
| 教学内容、回答证据提取、课程报告 | `gpt-oss:20b` | 质量优先，输出严格结构化 JSON |
| 教学路线规划、互动小题、学习主题候选 | `qwen3.5:4b` | 速度和质量平衡；先整理知识依赖/发现路径，再从资料总结主题并生成练习题 |
| 英文资料翻译、轻量摘要和元数据 | `qwen3.5:0.8b` | 先把英文/中英混排资料翻译为中文；失败时回退原文，不参与掌握度最终判断 |
| 扫描版/乱码 PDF 的视觉读取 | `deepseek-v4-flash-vision-exp` | 仅在显式开启视觉模式且已配置 DeepSeek 时使用 |

先确认 Ollama 服务和模型已就绪：

```powershell
ollama list
ollama ps
```

在被 Git 忽略的本机 `.env` 中设置（不要提交 `.env`）：

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=gpt-oss:20b
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
OLLAMA_QUALITY_MODEL=gpt-oss:20b
OLLAMA_BALANCED_MODEL=qwen3.5:4b
OLLAMA_FAST_MODEL=qwen3.5:0.8b
OLLAMA_TIMEOUT_SECONDS=300
OLLAMA_TRANSLATION_TIMEOUT_SECONDS=60
```

在 Ollama 模式下，英文/中英混排资料上传成功后会立即交给后台队列，由 `OLLAMA_FAST_MODEL` 分段翻译为中文并按文件 SHA-256 缓存；用户不需要等待翻译完成就能继续浏览资料库或生成课程。生成课程时优先读取已经完成的译文，仍在处理时先用原文生成，下一次生成会自动使用缓存结果。译文和原文会一起传入 `OLLAMA_QUALITY_MODEL`，证据引用仍只能来自原文，因此页码和引文可以回看。翻译不可用、超时、返回纯英文或单段失败时自动使用原文继续生成，不会阻塞课程保存。教学字段要求简体中文；若模型返回英文，服务会进行一次有界语言修复，仍不合格就保存中文资料导读草稿。学习页默认分析所选资料，由 `OLLAMA_BALANCED_MODEL` 后台总结多个学习主题供用户下拉选择，再自动推荐相关分卷；分析期间显示临时主题，不会阻塞课程生成。打开教学页时只抽样少量 PDF 页面，且按文件哈希复用本地样本缓存，不会为了列出主题而遍历整本教材。学习目标也改为预设选项，用户可选择重点方向，或选择由 AI 自动安排；提交后页面会实时显示已用时间和预计剩余时间，超过预估会标注仍在等待模型而不是伪造精确进度。掌握等级和下一步动作仍由本地 `Mastery Engine` 与 `Learning Policy` 决定；模型只提供可追溯的证据。若要对扫描 PDF 使用视觉读取，仍需沿用本机已有的 DeepSeek Key，并显式设置 `LLM_PAID_CALLS_ALLOWED=true`；没有视觉配置时，普通文字教学仍可正常使用。
在 Ollama 模式下，英文/中英混排资料上传成功后会立即交给后台队列，由 `OLLAMA_FAST_MODEL` 分段翻译为中文并按文件 SHA-256 缓存；用户不需要等待翻译完成就能继续浏览资料库或生成课程。生成课程时优先读取已经完成的译文，仍在处理时先用原文生成，下一次生成会自动使用缓存结果。译文和原文会一起传入 `OLLAMA_QUALITY_MODEL`，证据引用仍只能来自原文，因此页码和引文可以回看。翻译不可用、超时、返回纯英文或单段失败时自动使用原文继续生成，不会阻塞课程保存。教学字段要求简体中文；若模型返回英文，服务会进行一次有界语言修复，仍不合格就保存中文资料导读草稿。学习页默认分析所选资料，由 `OLLAMA_BALANCED_MODEL` 后台总结多个学习主题供用户下拉选择，再自动推荐相关分卷；分析期间显示临时主题，不会阻塞课程生成。生成正式课程前同一个平衡模型还会规划一份轻量 `TeachingPlan`，列出核心事实、知识依赖、为什么现在学、如何从资料发现，以及是否值得画图；规划失败会自动回退，不会阻塞课程。打开教学页时只抽样少量 PDF 页面，且按文件哈希复用本地样本缓存，不会为了列出主题而遍历整本教材。学习目标也改为预设选项，用户可选择重点方向，或选择由 AI 自动安排；提交后页面会实时显示已用时间和预计剩余时间，超过预估会标注仍在等待模型而不是伪造精确进度。掌握等级和下一步动作仍由本地 `Mastery Engine` 与 `Learning Policy` 决定；模型只提供可追溯的证据。若要对扫描 PDF 使用视觉读取，仍需沿用本机已有的 DeepSeek Key，并显式设置 `LLM_PAID_CALLS_ALLOWED=true`；没有视觉配置时，普通文字教学仍可正常使用。

## GitHub 协作流程

当前仓库保持私有。由于现有 GitHub 套餐不支持私有仓库分支保护，团队暂时通过流程约定保护 `main`：不要直接推送，所有修改使用短生命周期分支和 Pull Request，并在 CI 通过后合并。

```powershell
git switch main
git pull --ff-only
git switch -c feat/short-description

# 修改并运行检查

git add -p
git commit -m "feat: describe the change"
git push -u origin feat/short-description
```

随后在 GitHub 创建 Pull Request，填写模板并等待 CI。详细规范见 [CONTRIBUTING.md](CONTRIBUTING.md) 和
[协作者交接手册](docs/collaboration/HANDOFF.md)。当前代码所有者为 `@njr070907`。

## 项目结构

```text
app.py                         Streamlit 入口
src/ai_growth_companion/       应用、领域、Provider、仓库和 UI
src/ai_growth_companion/prompts/ 版本化 Prompt、清单与安全渲染
migrations/                    顺序执行的 SQLite 迁移
tests/unit/                    单元测试
tests/integration/             数据库与服务集成测试
tests/e2e/                     Streamlit 假闭环测试
scripts/                       Secret Scan 与真实启动检查
evals/golden/                  固定评测集与人工判分量表
docs/mastery-protocol/         Mastery Protocol 独立协议
.github/                       CI、Issue、PR 和代码所有者配置
```

## 关键文档

- [项目总上下文](docs/00_Project_Context_For_Codex.md)
- [最终主 PRD](docs/37_AI_Growth_Companion_Master_PRD.md)
- [Codex 启动指令](docs/38_Codex_Project_Kickoff_Instructions.md)
- [架构与数据流](docs/39_System_Architecture_and_Data_Flow.md)
- [测试与质量策略](docs/42_Test_and_Quality_Strategy.md)
- [隐私、安全与数据治理](docs/44_Privacy_Security_and_Data_Governance.md)
- [架构决策](docs/49_ADR_Architecture_Decision_Log.md)
- [完整文档索引](docs/51_Document_Index_and_Reading_Order.md)
- [Mastery Protocol](docs/mastery-protocol/README.md)
- [固定评测集与人工复核](evals/README.md)
- [协作者交接手册](docs/collaboration/HANDOFF.md)
- [变更记录](CHANGELOG.md)

## Sprint 0 停止条件

Sprint 0 的目标是搭建一个可以快速实验 Mastery Protocol 的可靠底座，不是继续增加基础设施。上述启动、迁移、Fake 场景、数据保存、端到端闭环和 CI 均通过后，应停止扩建 Sprint 0，进入 Sprint 1 验证真实 Mastery Protocol。

当前明确不引入 React、React Native、FastAPI、PostgreSQL、Redis、RAG、向量数据库、多 Agent、正式知识图谱、登录、支付或企业监控。

## 安全与许可证

不要提交 `.env`、API Key、本地数据库、日志、用户回答、数据导出或包含真实用户内容的原始评估结果。当前产品不是正式考试、医疗、心理、法律、人格、智力或职业诊断工具。安全报告方式见 [SECURITY.md](SECURITY.md)。

MVP 私有协作期暂不添加开源许可证。若仓库改为公开或接受外部贡献，所有者必须先明确许可证和贡献条款。
