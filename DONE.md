# Done

- Sprint 0 工程底座与最小 Fake 闭环（PR #1）。
- 20 条高数黄金评测集及逐项人工复核（PR #2）。
- Prompt `evaluator-v0.1`、确定性批量 Runner、Mastery Protocol v0.2 基线与 CI 回归（PR #3）。
- OpenAI Responses API 结构化评估适配器、付费安全门和离线失败测试（PR #4）。
- DeepSeek `deepseek-v4-flash-vision-exp` Chat Completions JSON Output 适配器、关闭思考模式、范围约束、受限 JSON 恢复和离线回归（PR #7–#11）。
- 结构化输出失败分类、字段级安全诊断和 JSON 值类型约束（PR #13–#15）。
- 指定模型同一知识点 4 场景真实基线：自动检查 4/4 通过。
- 指定模型完整 20 案例真实调用：20/20 结构成功，保存模型、Token、延迟、请求 ID 和失败诊断；多轮自动检查最高 19/20。
- GitHub 协作流程验证：功能分支、PR、CI、squash merge、合并后 main CI。
- 固定模型真实单案例的审计产物与失败原因已保存到本地 `evals/runs/`（该目录不进入 Git）。
