# 文档索引与阅读顺序

## 快速入口

### 开发者首次加入

按顺序阅读：`50_Project_README.md` → `37_AI_Growth_Companion_Master_PRD.md` → `38_Codex_Project_Kickoff_Instructions.md` → `39_System_Architecture_and_Data_Flow.md` → `42_Test_and_Quality_Strategy.md` → `44_Privacy_Security_and_Data_Governance.md` → `49_ADR_Architecture_Decision_Log.md`。

### 产品与用户研究

阅读：01、02、16、19、28、32、36、37、40、52。

### AI/Prompt 开发

阅读：03、04、07、12–15、17–19、26、29–31、33、37、42、45。

### 发布与值守

阅读：41–49，尤其是 43、46、47、48。

## 00–36 既有文档地图

> 本增补包无法读取原附件正文，下列名称依据原任务留下的目录记录。合并时应核对文件名；若原文件名略有差异，以原文件为准，不复制出第二份。

| 编号 | 文档 | 定位 |
|---|---|---|
| 00 | Project Context For Codex | 项目总上下文 |
| 01 | Product Blueprint | 愿景与蓝图 |
| 02 | MVP Function PRD | 原始 MVP 需求 |
| 03 | AI Agent Architecture | Agent 架构 |
| 04 | Cognitive Model Design | 认知模型 |
| 05 | Technical Architecture | 初始技术架构 |
| 06 | Codex Development Guide | Codex 协作规范 |
| 07 | Feynman Agent Implementation | 核心 Agent 设计 |
| 08 | Database Schema | 数据模型 |
| 09 | API Design | API 草案 |
| 10 | UI/UX Specification | 交互规范 |
| 11 | Development Roadmap | 路线图 |
| 12 | AI Safety and Alignment | AI 安全边界 |
| 13 | Prompt System Design | Prompt 体系 |
| 14 | RAG Knowledge System | 检索设计（P1） |
| 15 | Cognitive Engine Algorithm | 认知算法 |
| 16 | Product Constitution | 产品原则 |
| 17 | Growth Recommendation Engine | 推荐引擎（P1） |
| 18 | Learning Memory System | 记忆体系 |
| 19 | Evaluation Framework | 产品/学习效果评估 |
| 20 | Build With Codex Playbook | AI 辅助开发流程 |
| 21 | GitHub Project Structure | 仓库结构 |
| 22 | MVP Sprint Planning | Sprint 规划 |
| 23 | First Prototype Spec | 首个原型 |
| 24 | Testing Strategy | 旧版测试分层、Fake LLM 与关键不变量 |
| 25 | Local Development Setup | 本地环境 |
| 26 | Feynman Agent Code Architecture | 模块设计 |
| 27 | Codex First Build Prompt | 首次构建 Prompt |
| 28 | v0.1 Backlog | 优先级 |
| 29 | Feynman Agent Test Cases | AI 测试样例 |
| 30 | Prompt Evaluation System | Prompt 评估 |
| 31 | Cognitive Model v1 JSON Schema | 数据 Schema |
| 32 | MVP User Testing Protocol | 用户测试 |
| 33 | Feynman Agent MVP Code Spec | 工程规格 |
| 34 | Streamlit Prototype UI | 原型界面 |
| 35 | First 30 Days Build Plan | 个人执行计划 |
| 36 | Product Experiment Log Template | 实验记录模板 |

## 37–52 最终增补文档

| 编号 | 文档 | 权威范围 |
|---|---|---|
| 37 | AI Growth Companion Master PRD | 当前产品范围与验收 |
| 38 | Codex Project Kickoff Instructions | 开发启动指令 |
| 39 | System Architecture and Data Flow | 当前 MVP 架构 |
| 40 | Founder Decision Framework | 范围与决策纪律 |
| 41 | Engineering Execution Standard | 工程完成标准 |
| 42 | Test and Quality Strategy | 质量与发布门槛 |
| 43 | Deployment and Operations Runbook | 部署、恢复、维护 |
| 44 | Privacy Security and Data Governance | 数据与安全边界 |
| 45 | AI Model Governance | 模型、Prompt 与评价治理 |
| 46 | Data Migration Backup and Retention | Schema 生命周期 |
| 47 | Observability SLO and Incident Response | 监控与事件处理 |
| 48 | Release CI/CD and Rollback | 发布过程 |
| 49 | ADR Architecture Decision Log | 已接受架构决策 |
| 50 | Project README | 仓库首页草案 |
| 51 | Document Index and Reading Order | 唯一文档导航 |
| 52 | Completeness Audit and Documentation Freeze | 完备性结论与冻结线 |

## 开发期独立协议

| 文档 | 定位 |
|---|---|
| `mastery-protocol/README.md` | Mastery Protocol 的职责边界、结构化契约、事件证据与版本规则 |

## 冲突处理

同一主题有冲突时：适用法律与用户安全 > 44 隐私安全 > 37 主 PRD > 49 已接受 ADR > 42/45/46/48 操作标准 > 00–36 历史设计。冲突必须通过修改权威文档或新 ADR 消除，不能由代码自行选择。

## 维护规则

- 51 是唯一索引；不建立第二个目录文件。
- `mastery-protocol/README.md` 是由真实开发启动触发的独立协议，不作为第二份文档目录。
- 新事实优先更新现有权威文档。
- 已过期内容标记 Superseded，不静默删除决策历史。
- 每次正式发布只核对受影响文档，不做无意义全量重写。
