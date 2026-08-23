# GitHub 项目结构

## 1. 仓库目标

仓库既要支持个人 AI 辅助开发，也要让未来协作者快速理解产品、运行代码、复现实验和审查 AI 行为。

## 2. 推荐结构

```text
ai-growth-companion/
├─ app.py                       # Streamlit 入口
├─ src/
│  ├─ agents/                   # 问题生成与诊断
│  ├─ application/              # 用例编排
│  ├─ domain/                   # 领域模型与规则
│  ├─ infrastructure/           # LLM、数据库、日志
│  ├─ prompts/                  # 版本化 Prompt
│  └─ ui/                       # 页面与 View Model
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  ├─ e2e/
│  └─ fixtures/
├─ evals/
│  ├─ cases/                    # 诊断案例
│  ├─ rubrics/                  # 人工评分量表
│  └─ results/                  # 仅保存可公开的汇总
├─ docs/                        # 00–36 文档基线
├─ experiments/
│  └─ README.md                 # 实验索引；个人数据不提交
├─ scripts/                     # 初始化、迁移、评估
├─ data/
│  └─ .gitkeep                  # 数据库与个人数据忽略
├─ .github/
│  ├─ ISSUE_TEMPLATE/
│  └─ pull_request_template.md
├─ .env.example
├─ .gitignore
├─ pyproject.toml
├─ README.md
├─ CHANGELOG.md
└─ LICENSE                      # 确定开放策略后选择
```

## 3. 文档管理

- `docs/00_Project_Context_For_Codex.md` 是 AI 开发入口；
- 编号 00–36 作为 v0.1 基线，不随意重排；
- 需求变化在对应文档中更新并记录日期；
- 架构重大选择使用 ADR（后续从 37 起）；
- README 只保留项目介绍与快速启动，详细内容链接到 docs。

## 4. 分支策略

个人开发阶段采用轻量主干：

- `main`：始终可运行；
- `feat/<short-name>`：较大功能；
- `fix/<short-name>`：修复；
- 小改动可直接在短生命周期分支完成。

避免长期 `develop` 分支。合并前必须通过自动测试和一次手工核心流程。

## 5. Commit 规范

推荐：

```text
feat: save pending explanation before diagnosis
fix: preserve answer when model output is invalid
test: add misconception regression cases
docs: align MVP scope with prototype spec
```

提交描述“结果”，不使用“update files”这类无信息文本。

## 6. Issue 分类

标签建议：

- `type:feature`、`type:bug`、`type:experiment`、`type:docs`；
- `area:agent`、`area:data`、`area:ui`、`area:eval`；
- `priority:P0/P1/P2`；
- `risk:safety/privacy/data-loss`；
- `status:needs-evidence/ready/blocked`。

每个 Issue 包含用户价值、范围外、验收、验证和关联文档。

## 7. Milestone

- M0 Documentation Baseline；
- M1 Feynman Research Prototype；
- M2 Usable Streamlit Prototype；
- M3 30-Day Founder Experiment；
- M4 5–20 User Test；
- M5 Productization Decision。

里程碑代表假设验证，不代表堆积功能。

## 8. Pull Request 模板

```markdown
## 用户结果

## 范围与非目标

## 关键设计决定

## 测试与手工验证

## AI/数据安全检查
- [ ] 输出经过 Schema 校验
- [ ] 失败不丢用户输入
- [ ] 无 Key/个人数据泄露
- [ ] Prompt/Schema 版本已记录

## 截图或复现说明

## 已知限制
```

## 9. `.gitignore` 必须覆盖

```text
.env
.venv/
__pycache__/
.pytest_cache/
data/*.db
data/*.sqlite*
logs/
exports/
evals/results/raw/
*.pyc
```

根据工具补充，不忽略源码、迁移或测试 fixture。

## 10. 发布纪律

每个可使用版本打 tag，例如 `v0.1.0-prototype`；记录 Prompt、Schema、模型配置与数据库版本。个人原始学习数据不进入公开 Release。

