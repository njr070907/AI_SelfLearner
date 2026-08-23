# 本地开发环境

## 1. 目标

在 Windows 上用最少步骤运行和验证 Streamlit 原型。以下命令是目标形式，具体依赖版本以仓库 `pyproject.toml` 为准。

## 2. 前置工具

- Git；
- Python 3.11 或项目锁定版本；
- VS Code / Cursor / Codex 任选；
- 一个可用的 LLM API Key；
- 可选：GitHub 账号。

无需先安装 Node.js、Docker、PostgreSQL 或 Vector DB。

## 3. 获取项目

```powershell
git clone <repository-url>
Set-Location ai-growth-companion
```

## 4. 创建虚拟环境

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

若 PowerShell 阻止激活，优先参考组织/系统安全策略；不要永久降低整机安全设置。

## 5. 安装依赖

项目若使用标准 pip：

```powershell
pip install -e ".[dev]"
```

若仓库提供锁定工具，按 README 使用对应命令，避免混用多个环境管理器。

## 6. 环境变量

复制 `.env.example` 为 `.env`，填写本地值：

```text
LLM_API_KEY=replace-me
LLM_MODEL=project-default-model
DATABASE_URL=sqlite:///data/companion.db
APP_ENV=development
LOG_LEVEL=INFO
```

`.env` 必须在 `.gitignore` 中。不要把真实 Key 贴进 Prompt、截图、Issue 或日志。

## 7. 初始化

```powershell
python -m src.infrastructure.database init
```

如果项目采用其他入口，以 README 为准。初始化应可重复运行，不删除已有数据。

## 8. 启动

```powershell
streamlit run app.py
```

先使用 Fake LLM/演示模式贯通界面，再启用真实 API。

## 9. 测试与检查

```powershell
pytest
```

可选质量命令由项目定义，例如格式化、静态检查和类型检查。Codex 在交付前应运行相关命令并说明结果。

## 10. 常见问题

### 找不到 Python

确认安装版本和 `py -0p` 输出；不要同时混用 Microsoft Store 与多个未知环境。

### API Key 未读取

确认 `.env` 位置、变量名和启动目录。错误信息不得打印 Key 内容。

### 数据库锁定

关闭重复运行的应用实例，确认写事务短小。不要直接删除数据库；先备份并定位原因。

### 模型输出无效

查看脱敏日志中的 request id、Prompt/Schema 版本和错误类型；用户回答应仍在 History 中，使用重试功能。

## 11. AI 辅助开发工作流

1. 把任务与验收写清楚；
2. 让 Codex 先检查现有仓库；
3. 小步实现并运行测试；
4. 本人实际完成一次用户流程；
5. 把失败和决策写入实验日志；
6. 不直接接受未经运行验证的“完成”。

## 12. 数据备份

个人实验期间定期复制 `data/companion.db` 到受控备份位置；复制前停止写入或使用 SQLite 一致备份方式。备份同样包含个人数据，不上传公共仓库。

