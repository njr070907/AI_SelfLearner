# 技术架构

## 1. 架构原则

- 原型首先追求可运行、可观察、可修改；
- 业务逻辑与界面、模型供应商和数据库解耦；
- 所有 AI 输出先验证再保存为正式结构；
- 保留版本与原始证据，支持重放和比较；
- 仅在需求被验证后升级基础设施。

## 2. MVP 架构

```text
┌──────────────── Streamlit UI ────────────────┐
│ Home │ Session │ Diagnosis │ History         │
└──────────────────────┬───────────────────────┘
                       │
┌────────────── Application Services ──────────┐
│ SessionService │ DiagnosisService │ History  │
└──────────────┬───────────────┬───────────────┘
               │               │
┌──────── Domain ───────┐  ┌── AI Gateway ────┐
│ models / rules/schema │  │ prompts / client │
└──────────┬────────────┘  └─────────┬────────┘
           │                         │
┌──── Repository Layer ──┐       LLM API
│ SQLite + migrations    │
└────────────────────────┘
```

## 3. 推荐目录

```text
ai-growth-companion/
├─ app.py
├─ src/
│  ├─ agents/
│  │  ├─ question_generator.py
│  │  └─ evaluator.py
│  ├─ application/
│  │  ├─ session_service.py
│  │  └─ diagnosis_service.py
│  ├─ domain/
│  │  ├─ models.py
│  │  ├─ schemas.py
│  │  └─ scoring.py
│  ├─ infrastructure/
│  │  ├─ llm_client.py
│  │  ├─ database.py
│  │  └─ repositories.py
│  ├─ prompts/
│  │  ├─ question_v0_1.md
│  │  └─ evaluator_v0_1.md
│  └─ ui/
│     ├─ home.py
│     ├─ session.py
│     ├─ diagnosis.py
│     └─ history.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ fixtures/
├─ data/.gitkeep
├─ docs/
├─ .env.example
├─ pyproject.toml
└─ README.md
```

## 4. 数据流

1. UI 把输入转换为命令，不直接调用数据库或供应商 SDK。
2. Application Service 创建会话并调用问题生成器。
3. AI Gateway 组装 Prompt、发起请求、记录调用元数据。
4. Domain Schema 验证输出；失败进入一次修复/重试流程。
5. Repository 在事务中保存会话、问题、回答和诊断。
6. Cognitive Updater 根据新证据更新派生状态。
7. UI 从服务读取 View Model，不解析模型原始文本。

## 5. LLM Gateway

统一接口示例：

```python
class LLMClient(Protocol):
    def generate_structured(
        self,
        messages: list[Message],
        response_schema: type[BaseModel],
        *,
        model: str,
        timeout_seconds: int,
    ) -> LLMResult: ...
```

`LLMResult` 应包含解析数据、原始响应、模型名、用量、延迟、request id 和错误类型。业务代码不依赖特定 SDK 的返回对象。

## 6. 数据存储

MVP 使用 SQLite，开启外键与 WAL（如环境允许）。所有时间保存为 UTC。结构化字段优先使用关系字段；灵活诊断内容可保存 JSON 文本，同时保留可查询的关键列。

数据库变化必须通过可重复的初始化或迁移脚本完成，不在 UI 渲染时随意改表。

## 7. 配置

环境变量至少包括：

```text
LLM_API_KEY=
LLM_MODEL=
DATABASE_URL=sqlite:///data/companion.db
APP_ENV=development
LOG_LEVEL=INFO
```

禁止提供默认真实 Key。启动时验证必需配置，并给出可操作错误信息。

## 8. 错误与恢复

错误分类：输入错误、配置错误、模型超时、供应商错误、结构化解析错误、数据库错误、未知错误。界面显示人可理解的信息，日志保存技术细节但需脱敏。

关键恢复规则：用户回答先本地保存为 pending，再请求诊断；调用失败后用户可重试，无需重写回答。

## 9. 安全与隐私

- API Key 仅从环境读取；
- 日志默认不记录完整回答和模型原始输出；
- 用户数据导出与删除可在后续 P1 提供，但表结构需支持级联删除；
- 外部模型调用前明确数据边界；
- 不执行用户材料中的指令，材料仅作为不可信参考内容。

## 10. 可观察性

每次模型调用记录：会话 ID、用途、Prompt 版本、模型、耗时、成功/失败、重试次数、Schema 版本和 token 用量。不要记录 API Key；个人数据只记录必要标识或脱敏摘要。

## 11. 升级路径

当出现以下事实再升级：

- 需要多用户远程访问：加入 FastAPI、PostgreSQL 与认证；
- Streamlit 交互成为瓶颈：迁移 React/Electron；
- 材料规模导致上下文不足：加入对象存储、解析队列与 RAG；
- SQLite 并发或迁移不足：切换 PostgreSQL；
- 真实检索质量要求成立：评估 pgvector/Qdrant，而不是默认增加独立 Vector DB。

