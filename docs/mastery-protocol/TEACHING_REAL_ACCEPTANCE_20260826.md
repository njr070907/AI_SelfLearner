# 教学 Provider 真实受控验收记录（2026-08-26）

## 运行边界

- Provider：`deepseek`
- 模型：`deepseek-v4-flash-vision-exp`
- 付费调用：产品负责人在聊天中明确授权；只使用本机已有 `.env` Key，不输出、不提交 Key。
- 自动重试：无。
- 资料：临时合成的“函数极限” Markdown，不包含个人敏感信息。

## 适配器级结果

一次独立 Provider 请求成功返回 JSON：

- 输入 tokens：286
- 输出 tokens：1085
- 总 tokens：1371
- 返回字段：`schema_version`、`topic`、`title`、`summary`、`learning_objectives`、`sections`、`check_questions`、`interactive_checks`、`sources`
- Provider request id：`694d1d56-8a88-4645-8db5-ed8e72ae3733`

这证明固定模型和 Key 可以完成一次结构化教学内容响应；它不等于真实语义正确，也不等于已经通过应用服务层保存验收。

## 归一化修复

真实样本暴露了 Provider 与内部 Schema 的字段差异：`schema_version=1.0`、章节使用 `type`、检查问题为对象、来源为 ID 列表，部分答案可能使用索引。服务层新增归一化后再执行严格 Pydantic 校验，不放宽最终 Schema。

## 修复后端到端结果

新的独立受控请求已通过：

- 课程已写入新的隔离 SQLite 数据库。
- Provider：`deepseek`；模型：`deepseek-v4-flash-vision-exp`。
- Schema：`teaching-lesson-v0.2`。
- 章节：`concept`、`mechanism`、`boundary`、`example` 四类齐全。
- 互动题：3 道，结构有效。
- 每个章节的 `source_document_ids` 均指向选定资料。

## 当前结论

- 适配器级：通过。
- Teaching Schema 语义人工复核：未完成。
- `TeachingService` 端到端落库：归一化修复后通过一次新的受控请求。
- MVP 发布边界：仍保持待确认。

后续仍需人工检查讲解是否忠实于资料、例子是否正确、互动题答案是否合理；继续保持单次、零自动重试和脱敏记录。
