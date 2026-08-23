# Codex 项目启动指令

## 使用方式

把本文件与 `37_AI_Growth_Companion_Master_PRD.md`、`33_Feynman_Agent_MVP_Code_Spec.md` 一起交给 Codex。每次只执行一个可验收任务，不要一次性实现全部路线图。

## 项目背景

构建 AI Growth Companion v0.1：一个本地优先的费曼学习诊断原型。首版技术路径为 Python + Streamlit + SQLite，并通过可替换的 LLM Provider 访问模型。核心是可靠的学习诊断闭环，不是界面规模或 Agent 数量。

## 开发原则

1. 先实现最小端到端闭环，再增加抽象。
2. 所有模型输出都先做结构化校验，再进入数据库和 UI。
3. 业务代码不得直接依赖某个模型厂商 SDK；通过 Provider 接口隔离。
4. Prompt、模型名、参数和 Schema 都必须版本化。
5. 不在日志、测试夹具和提交历史中保存密钥或完整用户回答。
6. 每个功能同时提交测试、迁移、错误处理和必要文档。
7. 遇到文档冲突时，以主 PRD、隐私治理、模型治理、ADR 的顺序裁决；仍无法裁决则停止并记录问题。

## 推荐首版目录

```text
app/
  ui/
  domain/
  agents/
  services/
  repositories/
  providers/
  schemas/
  prompts/
  observability/
migrations/
tests/
  unit/
  integration/
  e2e/
  evals/
scripts/
docs/
.env.example
pyproject.toml
README.md
```

## Sprint 0：可运行骨架

交付：

- 建立项目、依赖锁定、格式化、静态检查和测试命令。
- `.env.example` 只列变量名与说明，不含真实值。
- SQLite 连接、迁移框架和健康检查。
- LLM Provider 接口及 Fake Provider。
- Streamlit 空壳页面可启动。
- CI 至少执行 lint、类型检查、单元测试和密钥扫描。

验收：全新环境按 README 能在 15 分钟内启动；没有 API Key 时 Fake Provider 可完成演示。

## Sprint 1：费曼闭环

交付：主题输入、问题生成、用户回答、结构化诊断、结果展示和持久化。模型失败、超时、格式错误都有可恢复路径。使用请求 ID 防止重复写入。

验收：至少 10 条黄金样例端到端通过；断网、无效 JSON、重复提交和空回答均有自动测试。

## Sprint 2：历史与反馈

交付：历史列表、详情、诊断反馈、导出与删除。认知画像只能引用证据，且允许用户纠正。

验收：删除后业务数据不可在 UI/API 中再次读取；导出内容与数据字典一致；用户纠错会改变后续聚合结果。

## 每个任务的完成格式

Codex 完成任务时必须报告：

- 改了什么，以及为什么。
- 修改的文件与迁移编号。
- 运行了哪些检查，结果如何。
- 已知限制与下一项最小任务。
- 是否改变数据、隐私、模型行为或运行方式；若改变，指出需更新的文档或 ADR。

## 禁止事项

- 未经指标证明就引入 FastAPI、PostgreSQL、向量数据库或多 Agent。
- 绕过测试来“先跑起来”。
- 在失败时编造诊断、默认高置信度或隐藏模型限制。
- 自动执行不可逆生产数据删除、生产迁移或发布。
- 把未来 P1/P2 写成当前已经支持的能力。

## 第一条开发指令

> 阅读 37、38、42、44、45、46、48、49。只执行 Sprint 0：建立最小可运行骨架、Fake Provider、SQLite 迁移、健康检查和 CI。先列出将创建的文件及验收测试；实现后运行全部检查，并按“每个任务的完成格式”报告。不要实现真实诊断业务，也不要引入未获批准的基础设施。

