# 数据库 Schema

## 1. 目标

MVP 使用 SQLite 保存可追溯的学习证据。设计优先保证：原始事实不丢失、AI 派生结论可重算、版本可追踪、用户数据可删除。

## 2. 关系概览

```text
users 1──N learning_sessions
learning_sessions 1──1 feynman_questions
learning_sessions 1──N user_explanations
user_explanations 1──N diagnoses
users 1──N knowledge_states N──1 concepts
diagnoses 1──N cognitive_evidence
users 1──N cognitive_patterns
concepts N──N concepts (knowledge_relations, later)
```

## 3. MVP 表

### 3.1 users

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | TEXT | PK | UUID |
| display_name | TEXT | NOT NULL | 本地用户可为 `default` |
| locale | TEXT | NOT NULL | 默认 `zh-CN` |
| created_at | TEXT | NOT NULL | UTC ISO-8601 |
| updated_at | TEXT | NOT NULL | UTC ISO-8601 |

### 3.2 concepts

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | TEXT | PK | UUID |
| normalized_name | TEXT | NOT NULL | 规范名 |
| display_name | TEXT | NOT NULL | 展示名 |
| domain | TEXT | NULL | 数学/编程等 |
| description | TEXT | NULL | 可选 |
| created_at | TEXT | NOT NULL | UTC |

建议对 `normalized_name, domain` 建唯一索引；不要仅依靠字符串自动合并语义不同的概念。

### 3.3 learning_sessions

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | TEXT | PK | UUID |
| user_id | TEXT | FK users | 用户 |
| concept_id | TEXT | FK concepts | 概念 |
| status | TEXT | NOT NULL | created/questioned/answered/diagnosed/failed |
| learning_goal | TEXT | NULL | 当前目标 |
| learner_level | TEXT | NULL | 自评水平 |
| started_at | TEXT | NOT NULL | UTC |
| completed_at | TEXT | NULL | UTC |
| error_code | TEXT | NULL | 最后错误 |

### 3.4 feynman_questions

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | TEXT | PK | UUID |
| session_id | TEXT | FK + UNIQUE | 所属会话 |
| question_text | TEXT | NOT NULL | 问题原文 |
| coverage_points_json | TEXT | NOT NULL | JSON 数组 |
| difficulty | TEXT | NOT NULL | 难度 |
| question_type | TEXT | NOT NULL | mechanism/transfer/etc. |
| prompt_version | TEXT | NOT NULL | Prompt 版本 |
| model_name | TEXT | NOT NULL | 模型 |
| raw_response | TEXT | NULL | 调试用途，注意隐私 |
| created_at | TEXT | NOT NULL | UTC |

### 3.5 user_explanations

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | TEXT | PK | UUID |
| session_id | TEXT | FK | 所属会话 |
| question_id | TEXT | FK | 对应问题 |
| answer_text | TEXT | NOT NULL | 用户原文 |
| answer_type | TEXT | NOT NULL | main/follow_up |
| sequence_no | INTEGER | NOT NULL | 回答序号 |
| created_at | TEXT | NOT NULL | UTC |

### 3.6 diagnoses

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | TEXT | PK | UUID |
| explanation_id | TEXT | FK | 对应回答 |
| status | TEXT | NOT NULL | pending/succeeded/failed |
| summary | TEXT | NULL | 摘要 |
| mastery_level | TEXT | NULL | 枚举 |
| correctness | INTEGER | NULL | 0–100 |
| mechanism_understanding | INTEGER | NULL | 0–100 |
| depth | INTEGER | NULL | 0–100 |
| transfer | INTEGER | NULL | 0–100/NULL |
| confidence | REAL | NULL | 0–1 |
| result_json | TEXT | NULL | 完整结构化结果 |
| raw_response | TEXT | NULL | 原始模型输出 |
| prompt_version | TEXT | NOT NULL | Prompt 版本 |
| schema_version | TEXT | NOT NULL | Schema 版本 |
| model_name | TEXT | NOT NULL | 模型 |
| latency_ms | INTEGER | NULL | 延迟 |
| error_code | TEXT | NULL | 失败原因 |
| created_at | TEXT | NOT NULL | UTC |

### 3.7 diagnosis_feedback

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | TEXT | PK | UUID |
| diagnosis_id | TEXT | FK | 诊断 |
| user_id | TEXT | FK | 用户 |
| rating | TEXT | NOT NULL | accurate/partial/inaccurate |
| comment | TEXT | NULL | 说明 |
| created_at | TEXT | NOT NULL | UTC |

### 3.8 knowledge_states

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | TEXT | PK | UUID |
| user_id | TEXT | FK | 用户 |
| concept_id | TEXT | FK | 概念 |
| mastery_level | TEXT | NOT NULL | 当前估计 |
| score | REAL | NULL | 内部连续值 |
| confidence | REAL | NOT NULL | 证据充分度 |
| evidence_count | INTEGER | NOT NULL | 样本数 |
| last_diagnosis_id | TEXT | FK | 最近证据 |
| state_version | TEXT | NOT NULL | 算法版本 |
| updated_at | TEXT | NOT NULL | UTC |

唯一索引：`user_id, concept_id`。

### 3.9 cognitive_evidence

记录支持或反驳某状态/模式的原子证据：`id`、`user_id`、`diagnosis_id`、`concept_id`、`evidence_type`、`claim`、`answer_excerpt`、`polarity`、`weight`、`confidence`、`created_at`。

## 4. P1/P2 表

- `goals`：长期目标与版本；
- `documents`、`document_chunks`：材料与来源；
- `knowledge_relations`：前置、组成、对比关系；
- `cognitive_patterns`：候选/稳定模式、置信度与状态；
- `pattern_evidence_links`：模式与正反证据多对多；
- `growth_reports`：周期报告快照；
- `prompt_runs`：统一模型调用审计。

## 5. 数据原则

- 原始回答、原始模型输出与派生状态分开；
- 更新状态不覆盖历史诊断；
- JSON 字段必须有 Schema 版本；
- 删除用户时级联删除原始与派生数据；
- 日志与数据库不保存 API Key；
- 敏感文本的备份、导出与外部发送需明确边界。

## 6. 索引建议

- `learning_sessions(user_id, started_at DESC)`；
- `learning_sessions(concept_id, started_at DESC)`；
- `diagnoses(explanation_id, created_at DESC)`；
- `knowledge_states(user_id, updated_at DESC)`；
- `cognitive_evidence(user_id, evidence_type, created_at DESC)`。

## 7. 迁移与测试

- 初始化幂等；
- 测试外键、唯一约束与级联删除；
- 每次 Schema 变更包含向前迁移和备份说明；
- 使用临时数据库运行集成测试；
- 验证 UTC、中文、长文本、引号和 Emoji。

