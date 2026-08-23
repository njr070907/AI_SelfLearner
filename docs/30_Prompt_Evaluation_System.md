# Prompt Evaluation System

## 1. 目标

用可重复实验替代凭感觉修改 Prompt，持续提高准确性、解释性、校准和帮助度。

## 2. 迭代闭环

```text
提出失败假设
    ↓
冻结评估集与基线
    ↓
创建 Prompt 候选版本
    ↓
批量运行相同案例
    ↓
盲评 + 自动结构检查
    ↓
比较质量、成本、延迟和安全
    ↓
采用 / 拒绝 / 修订
    ↓
记录版本与原因
```

## 3. 目录

```text
evals/
├─ cases/
│  ├─ math.yaml
│  ├─ programming.yaml
│  ├─ ai.yaml
│  └─ economics.yaml
├─ rubrics/
│  └─ diagnosis_rubric.md
├─ runs/
│  └─ .gitkeep
├─ baselines/
│  └─ evaluator-v0.1.json
└─ run_eval.py
```

含真实用户内容的原始 runs 默认不提交。

## 4. 版本记录

每次运行保存：

- run id、时间、提交 hash；
- Prompt 与 Schema 版本；
- 模型及参数；
- 案例集版本；
- 每个案例原始与解析输出；
- 延迟、token 和估算成本；
- 自动检查结果；
- 人工评分；
- 采用决策。

## 5. 自动检查

- JSON/Schema 合法；
- 分数范围与枚举；
- `evidence` 片段是否真的出现在回答；
- 误区是否有证据字段；
- 空回答是否错误输出高掌握；
- 是否出现禁用人格化词式；
- 是否只有一个主要追问/建议；
- 输出长度、延迟与成本。

自动检查不能替代语义人工评审。

## 6. 人工评分量表

每维 1–5：

1. **Accuracy**：事实与核心诊断是否正确；
2. **Coverage**：关键正确点、缺失和误区是否覆盖；
3. **Evidence**：结论是否由原回答支持；
4. **Calibration**：确定性是否符合证据；
5. **Helpfulness**：追问和下一步是否有效；
6. **Safety**：是否尊重边界和用户主体性。

另设严重错误标记：虚构证据、反向误区、人格定性、执行注入、敏感数据泄露。

## 7. A/B 规则

- 一次只改变一个主要因素；
- 同一案例、模型和参数；
- 随机隐藏 A/B 身份；
- 不只看平均分，检查关键案例回退；
- 样本小时报告不确定性，不声称显著性；
- 成本或延迟显著上升必须有价值补偿。

## 8. 采用门槛

新 Prompt 至少满足：

- 结构成功率不低于基线；
- 目标问题明显改善；
- 严重安全错误为 0；
- 核心误区案例不回退；
- Calibration 不恶化；
- 成本和延迟可接受。

若只改善文案“好看”，但诊断无提升，不升级核心版本。

## 9. 线上反馈回流

以下事件进入候选回归队列：

- 用户标记“不准确”；
- 高置信度诊断随后被反证；
- 解析失败；
- 用户反复忽略建议并说明无关；
- 人工发现安全越界。

必须脱敏、取得适当授权并由人标注后再进入评估集。

## 10. 实验报告模板

```markdown
# Prompt Experiment
- ID:
- Date:
- Hypothesis:
- Baseline:
- Candidate:
- Changed variable:
- Dataset:
- Results by dimension:
- Critical regressions:
- Cost / latency:
- Reviewer notes:
- Decision:
- Follow-up:
```

## 11. 防止评估污染

- 保留一组不参与日常调参的 holdout；
- Few-shot 示例与评估题分离；
- 不根据单个案例写过度专用规则；
- 定期增加不同表达和跨领域案例；
- 记录模型升级，不能把模型变化归功于 Prompt。

