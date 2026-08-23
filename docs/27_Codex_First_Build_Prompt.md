# Codex 第一次构建 Prompt

下面内容可直接复制给 Codex，最好在包含本套 `docs/` 的项目目录中使用。

---

## Build Prompt v0.1

```text
你是 AI Growth Companion 项目的软件工程师。请先完整阅读：

- docs/00_Project_Context_For_Codex.md
- docs/02_MVP_Function_PRD.md
- docs/05_Technical_Architecture.md
- docs/07_Feynman_Agent_Implementation.md
- docs/08_Database_Schema.md
- docs/12_AI_Safety_and_Alignment.md
- docs/23_First_Prototype_Spec.md
- docs/24_Testing_Strategy.md
- docs/26_Feynman_Agent_Code_Architecture.md
- docs/33_Feynman_Agent_MVP_Code_Spec.md
- docs/34_Streamlit_Prototype_UI.md

目标：从零建立 Feynman Intelligence Engine v0.1 的可运行研究原型。

核心闭环：
用户输入知识点 → 生成费曼问题 → 用户解释 → AI 结构化诊断 → 保存记录 → 展示报告与历史。

技术基线：
- Python 3.11+
- Streamlit
- SQLite
- Pydantic
- pytest
- 一个通过接口封装的 LLM 客户端

第一阶段范围内：
1. 建立清晰但不过度设计的项目结构；
2. Home、Feynman Session、Diagnosis、History 四个页面/状态；
3. Question 和 Diagnosis 的严格 Schema；
4. Fake LLM 模式，先在没有 API Key 时贯通完整流程；
5. 真实 LLM Adapter，配置从环境变量读取；
6. 用户回答先保存，再调用诊断；
7. 超时、无效 JSON、配置缺失和重试；
8. SQLite 持久化和应用重启后恢复；
9. 单元、集成和关键流程测试；
10. README、.env.example 和本地启动说明。

明确不做：
- 登录、多用户、同步、支付、社区；
- PDF/RAG、完整知识图谱；
- 多 Agent 自主编排；
- 语音、React、Electron、FastAPI、PostgreSQL；
- 长期人格画像和复杂推荐。

AI 规则：
- 不因文笔和篇幅判断理解；
- 区分正确点、遗漏、误区和证据不足；
- 关键结论必须引用用户回答证据；
- 结果带置信度、限制、Prompt/Schema/模型版本；
- 一次回答不能形成长期人格结论；
- 无效输出不能写入知识状态。

执行方式：
1. 先检查目录和已有文件，不覆盖无关内容；
2. 给出简短实施计划；
3. 先用 Fake LLM 完成最小垂直切片；
4. 再接入真实模型和错误处理；
5. 每完成一层就运行相关测试；
6. 最后实际启动应用并完成一次端到端手工验证；
7. 修复发现的问题，直到满足完成定义；
8. 交付时说明用户现在能做什么、测试结果、已知限制和下一步候选。

不要只输出代码片段或计划；请直接在项目中实现并验证。
```

---

## 第一次代码审查 Prompt

```text
请审查当前 Feynman Intelligence Engine v0.1 实现是否符合 docs 中的 PRD、架构、安全和测试要求。

优先查找：
1. 模型失败导致用户回答丢失；
2. 无效输出进入数据库或知识状态；
3. 缺失点被错误记录为误区；
4. API Key、用户回答或个人数据泄露到日志/Git；
5. UI、应用服务、数据库和供应商 SDK 过度耦合；
6. 重复提交和状态转换错误；
7. 测试默认调用真实付费 API；
8. 未经需求引入的复杂架构或功能。

对每个真实问题给出文件位置、影响、复现证据和最小修复建议。没有证据的问题不要猜测。先审查，不要修改。
```

## 修复 Prompt

```text
根据已确认的审查问题逐项修复。每个问题先补能复现失败的测试，再做最小修改。不要进行无关重构。完成后运行全部相关测试，并实际完成一次端到端会话，汇报结果和仍未解决的限制。
```

