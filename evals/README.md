# 固定评测集

`evals/golden/high_math_v0.1.json` 是 Sprint 1 的第一份黄金评测集。它用于回答一个具体问题：系统能否稳定区分“回答充分”“部分正确”“存在明确误区”和“证据不足”，而不是把表达流畅度当成掌握程度。

当前状态：`approved`。20 个案例已由 `njr070907` 逐项完成人工复核。通过表示案例内容和期望量表可作为第一版回归基线，不表示真实模型已经达到这些要求。

## 当前内容

评测集包含 5 个高等数学知识点，每个知识点各有 4 类模拟学习者回答，共 20 个案例：

1. 函数极限存在与左右极限；
2. 等价无穷小替换的条件与加减陷阱；
3. 连续、可导与可微的关系；
4. 洛必达法则的适用条件；
5. 定积分定义、符号面积与变上限积分。

每个案例包含问题、原创模拟回答、覆盖点、期望证据、缺口、可能误区、禁止结论、允许的掌握等级、建议动作、置信度区间、来源页码和人工复核状态。

## 来源与版权边界

- 原始讲义 PDF 只作为本地事实核对材料，不提交到仓库。
- 仓库只保存原创问题、原创模拟回答、人工量表、文件哈希和页码来源。
- 不复制讲义中的长段文字、图片或整页内容。
- 文件哈希用于确认复核者看到的是同一版本，不包含本地绝对路径。

这批 PDF 是评测材料来源，不是应用运行时的知识库，也不表示项目已经决定建设 RAG 或上传材料功能。

## 自动校验

```powershell
uv run python scripts/validate_golden_set.py
uv run pytest tests/unit/test_golden_set.py
```

校验会确保：

- 恰好有 5 个知识点和 20 个案例；
- 每个知识点完整覆盖四类回答；
- `partial`、`misconception`、`insufficient_evidence` 都禁止 `solid`；
- 来源文档与页码存在且没有越界；
- 案例 ID 和来源 ID 唯一；
- 未完成人工复核时，数据集不能标记为 `approved`。

自动校验只证明数据结构自洽，不证明数学内容正确。

## 批量运行

零成本检查 20 个 Prompt 输入信封能否正确渲染：

```powershell
uv run python scripts/run_golden_eval.py --dry-run
```

Prompt v0.2 是当前候选实验版本，默认不会替换 v0.1。先用一个或几个固定 `case_id` 做零成本渲染检查：

```powershell
uv run python scripts/run_golden_eval.py `
  --prompt-version v0.2 `
  --case-id hm-lhopital-strong `
  --dry-run
```

运行免费的确定性 Fake 管道基线：

```powershell
uv run python scripts/run_golden_eval.py
```

在 API Key 和费用得到明确授权、且完成小范围实验设计后，才可以运行 DeepSeek JSON Output 适配器。模型固定为 `deepseek-v4-flash-vision-exp`，真实模式默认只跑 1 条、每条零重试：

```powershell
uv run python scripts/run_golden_eval.py --provider deepseek --confirm-paid-calls
```

运行前需在本机 `.env` 设置 `LLM_PROVIDER=deepseek`、`LLM_API_KEY`；适配器会固定使用 `deepseek-v4-flash-vision-exp`。扩大批量必须显式传入 `--max-cases`。不要将 Key 或真实运行产物提交到仓库。

运行记录保存在被 Git 忽略的 `evals/runs/`，包含数据集、Prompt、Provider、模型、Schema、协议、动作、用量、自动检查和错误版本信息。Fake 模式不会真正把 Prompt 发给模型，运行记录会明确保存 `prompt_applied_to_provider=false`。

自动检查覆盖结构、证据原文、观察形状、掌握等级、动作与置信度范围。它不能判断自然语言诊断是否真正表达了量表中的数学语义，因此所有成功结果仍标记为需要人工语义复核。

## 人工复核方法

复核者逐个案例检查：

1. 问题和答案是否符合所引用讲义页的知识范围；
2. `scenario` 是否与回答质量一致；
3. 期望证据、缺口和误区是否都能由回答原文支持；
4. 是否遗漏了会改变判断的关键数学条件；
5. 允许/禁止的掌握等级是否保守；
6. 推荐动作是否是最小、可执行的下一步。

确认后将该案例的 `human_review` 改为：

```json
{
  "status": "approved",
  "reviewer": "GitHub 用户名或姓名",
  "reviewed_at": "2026-08-23T12:00:00+08:00",
  "notes": []
}
```

如果需要修改，使用 `changes_requested` 并在 `notes` 写清原因。只有 20 个案例全部通过后，才把数据集顶层 `status` 改为 `approved`。任何 Prompt、模型或 Mastery Protocol 的实验都应保留本次运行结果和版本信息，但真实用户回答不得提交到仓库。

## 首轮复核形成的协议规则

- 只会复述规则、公式或题目已经提示的经典例子，仍属于 `fragile`，不能直接进入 `developing`。
- `partial` 描述回答里有部分正确内容，不等同于掌握等级 `developing`。
- `insufficient_evidence` 表示无法识别具体误区；当回答者明确不会解释或应用时，仍可高置信度判定“当前未掌握（not_evident）”。
- 一次未掌握只描述当前证据，不能扩大成永久没有知识储备或能力判断。
- 从 `fragile` 升级到 `developing`，至少需要未提示的新例子、边界判断或迁移任务作为证据。
