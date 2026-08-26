# Cognitive Model v1 JSON Schema

## 1. 原则

该 Schema 是长期数据交换模型，不要求 MVP 一次实现所有字段。字段必须区分用户自述、观察事实、AI 派生结论和置信度。

## 2. 示例实例

```json
{
  "schema_version": "cognitive-profile-v1",
  "user_id": "uuid",
  "generated_at": "2026-08-23T00:00:00Z",
  "goals": [
    {
      "goal_id": "uuid",
      "title": "掌握机器学习基础",
      "purpose": "完成课程并能做项目",
      "status": "active",
      "priority": "high",
      "target_date": null,
      "source": "user_report",
      "updated_at": "2026-08-23T00:00:00Z"
    }
  ],
  "knowledge_state": {
    "concepts": [
      {
        "concept_id": "uuid",
        "name": "梯度下降",
        "domain": "machine_learning",
        "mastery_level": "developing",
        "dimensions": {
          "correctness": 78,
          "mechanism_understanding": 62,
          "application": null,
          "retention": null
        },
        "confidence": 0.68,
        "evidence_count": 3,
        "active_misconception_ids": [],
        "last_evaluated_at": "2026-08-23T00:00:00Z",
        "state_version": "cognitive-v0.1"
      }
    ]
  },
  "abilities": [
    {
      "ability": "mechanism_explanation",
      "observation": "在当前机器学习概念中能描述目标，但机制细节不稳定",
      "scope": {"domains": ["machine_learning"]},
      "evidence_ids": ["e1", "e2"],
      "counter_evidence_ids": [],
      "confidence": 0.54,
      "status": "candidate"
    }
  ],
  "thinking_patterns": [
    {
      "pattern_id": "uuid",
      "type": "result_without_mechanism",
      "description": "有时先描述结果，但未说明产生结果的机制",
      "scope": {"domains": ["machine_learning", "economics"]},
      "evidence_ids": ["e1", "e8", "e12"],
      "counter_evidence_ids": ["e15"],
      "confidence": 0.63,
      "status": "candidate",
      "user_feedback": "partial"
    }
  ],
  "learning_behavior": {
    "observation_window_days": 30,
    "sessions_completed": 18,
    "active_days": 12,
    "repeat_evaluations": 6,
    "recommendation_acceptance_rate": 0.58,
    "facts_only": true
  },
  "effective_preferences": [
    {
      "preference": "overview_before_details",
      "claim": "先看概念关系后进行解释时，复测表现更稳定",
      "evidence_ids": ["e20", "e21"],
      "confidence": 0.47,
      "status": "experimental"
    }
  ],
  "limitations": [
    "当前样本主要来自机器学习领域",
    "应用能力证据不足"
  ]
}
```

## 3. JSON Schema（核心版）

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.local/schemas/cognitive-profile-v1.json",
  "title": "CognitiveProfileV1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "user_id",
    "generated_at",
    "goals",
    "knowledge_state",
    "abilities",
    "thinking_patterns",
    "learning_behavior",
    "effective_preferences",
    "limitations"
  ],
  "properties": {
    "schema_version": {"const": "cognitive-profile-v1"},
    "user_id": {"type": "string", "minLength": 1},
    "generated_at": {"type": "string", "format": "date-time"},
    "goals": {
      "type": "array",
      "items": {"$ref": "#/$defs/goal"}
    },
    "knowledge_state": {
      "type": "object",
      "additionalProperties": false,
      "required": ["concepts"],
      "properties": {
        "concepts": {
          "type": "array",
          "items": {"$ref": "#/$defs/conceptState"}
        }
      }
    },
    "abilities": {
      "type": "array",
      "items": {"$ref": "#/$defs/evidenceClaim"}
    },
    "thinking_patterns": {
      "type": "array",
      "items": {"$ref": "#/$defs/pattern"}
    },
    "learning_behavior": {
      "type": "object",
      "additionalProperties": true,
      "required": ["observation_window_days", "facts_only"],
      "properties": {
        "observation_window_days": {"type": "integer", "minimum": 1},
        "sessions_completed": {"type": "integer", "minimum": 0},
        "active_days": {"type": "integer", "minimum": 0},
        "repeat_evaluations": {"type": "integer", "minimum": 0},
        "recommendation_acceptance_rate": {
          "type": ["number", "null"], "minimum": 0, "maximum": 1
        },
        "facts_only": {"const": true}
      }
    },
    "effective_preferences": {
      "type": "array",
      "items": {"$ref": "#/$defs/evidenceClaim"}
    },
    "limitations": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "$defs": {
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "status": {
      "type": "string",
      "enum": ["experimental", "candidate", "supported", "disputed", "archived"]
    },
    "scope": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "domains": {"type": "array", "items": {"type": "string"}},
        "time_range": {"type": ["string", "null"]}
      }
    },
    "goal": {
      "type": "object",
      "additionalProperties": false,
      "required": ["goal_id", "title", "status", "source", "updated_at"],
      "properties": {
        "goal_id": {"type": "string"},
        "title": {"type": "string", "minLength": 1},
        "purpose": {"type": ["string", "null"]},
        "status": {"enum": ["active", "paused", "completed", "archived"]},
        "priority": {"enum": ["low", "medium", "high"]},
        "target_date": {"type": ["string", "null"], "format": "date"},
        "source": {"enum": ["user_report", "imported"]},
        "updated_at": {"type": "string", "format": "date-time"}
      }
    },
    "dimensions": {
      "type": "object",
      "additionalProperties": false,
      "required": ["correctness", "mechanism_understanding", "application", "retention"],
      "properties": {
        "correctness": {"type": ["number", "null"], "minimum": 0, "maximum": 100},
        "mechanism_understanding": {"type": ["number", "null"], "minimum": 0, "maximum": 100},
        "application": {"type": ["number", "null"], "minimum": 0, "maximum": 100},
        "retention": {"type": ["number", "null"], "minimum": 0, "maximum": 100}
      }
    },
    "conceptState": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "concept_id", "name", "mastery_level", "dimensions", "confidence",
        "evidence_count", "active_misconception_ids", "last_evaluated_at", "state_version"
      ],
      "properties": {
        "concept_id": {"type": "string"},
        "name": {"type": "string"},
        "domain": {"type": ["string", "null"]},
        "mastery_level": {"enum": ["no_clue", "fragile", "developing", "solid"]},
        "dimensions": {"$ref": "#/$defs/dimensions"},
        "confidence": {"$ref": "#/$defs/confidence"},
        "evidence_count": {"type": "integer", "minimum": 0},
        "active_misconception_ids": {"type": "array", "items": {"type": "string"}},
        "last_evaluated_at": {"type": ["string", "null"], "format": "date-time"},
        "state_version": {"type": "string"}
      }
    },
    "evidenceClaim": {
      "type": "object",
      "additionalProperties": true,
      "required": ["claim", "evidence_ids", "counter_evidence_ids", "confidence", "status"],
      "properties": {
        "claim": {"type": "string"},
        "scope": {"$ref": "#/$defs/scope"},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
        "counter_evidence_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"$ref": "#/$defs/confidence"},
        "status": {"$ref": "#/$defs/status"}
      }
    },
    "pattern": {
      "allOf": [
        {"$ref": "#/$defs/evidenceClaim"},
        {
          "type": "object",
          "required": ["pattern_id", "type", "description"],
          "properties": {
            "pattern_id": {"type": "string"},
            "type": {"type": "string"},
            "description": {"type": "string"},
            "user_feedback": {"enum": ["accurate", "partial", "inaccurate", null]}
          }
        }
      ]
    }
  }
}
```

## 4. 实现说明

- 数据库是事实源，JSON Profile 是可导出快照；
- `null` 表示没有证据，不等于 0；
- 行为层只存观察事实，不自动推断动机；
- `additionalProperties` 在过渡模块中可暂时开放，但正式核心对象应严格；
- Schema 变更必须升级版本并提供迁移/重算策略；
- 用户删除证据后，Profile 必须重算。

## 5. MVP 子集

第一版只要求 `user_id`、`knowledge_state.concepts`、`limitations` 和版本元数据。Goals、Abilities、Patterns、Behavior、Preferences 随实验逐步启用。
