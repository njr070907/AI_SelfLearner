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

## 单案例人工语义复核

对上述隔离课程的生成内容逐项回看后，得到以下结果：

- 导学主题、摘要和学习目标均围绕“函数极限”，没有脱离上传资料。
- 左右极限存在且相等才有极限、左右极限不等时极限不存在等核心表述正确。
- 分段函数在 `x=1` 处左极限为 1、右极限为 2 的例子计算正确。
- `|x|/x` 在 `x→0` 时极限不存在的互动题、选项、答案和解析一致。
- 互动题答案均能在选项中找到，解析与题目结论一致；章节来源 ID 均指向本次合成资料。

结论：该合成资料的单案例真实语义复核通过。这个结果只证明一个受控数学案例质量可接受，不外推为所有资料类型、所有主题或正式发布结论。

## 当前结论

- 适配器级：通过。
- 单个合成数学案例的 Teaching Schema 语义人工复核：通过。
- `TeachingService` 端到端落库：归一化修复后通过一次新的受控请求。
- 全量真实资料语义复核与 MVP 发布边界：仍保持待确认。

后续仍需人工检查讲解是否忠实于资料、例子是否正确、互动题答案是否合理；继续保持单次、零自动重试和脱敏记录。
