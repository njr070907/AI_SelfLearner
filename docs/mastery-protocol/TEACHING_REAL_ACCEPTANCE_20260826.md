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
- 更广泛真实资料语义复核与 MVP 发布边界：仍保持待确认。

## 跨文档受控调用发现

使用仓库内 `docs/02_MVP_Function_PRD.md` 做第二个真实教学案例时，模型配置和 Key 均通过安全门，但响应以 `finish_reason=length` 截断，服务按设计拒绝落库（`LLM_OUTPUT_TRUNCATED`）。该失败没有自动重试，也没有产生半成品课程。

根因是教学适配器默认 `max_tokens=2,000` 对较长 PRD 不足；已将默认上限提高到 4,000，并增加 500–8,000 的本地参数边界和离线契约断言。修复后是否能稳定完成跨文档真实语义验收，仍需后续在明确授权下单次验证。

随后一次修复验证未截断，但模型省略了四个章节的 `section_type`，严格 Schema 再次拒绝落库。Prompt 已明确要求该字段，服务层仅对“恰好四段且保持 `concept → mechanism → boundary → example` 顺序”的响应做受限补全，并加入离线测试；任意其他形状仍会失败，不会静默接受未知章节。

## 第二个真实案例修复后结果

使用同一份 `docs/02_MVP_Function_PRD.md`，以主题 `MVP` 重新执行一次新的受控请求后通过：

- 课程已写入隔离 SQLite，`lesson_id=6bc5a3e8-e273-404f-a7dd-3963ed10f7db`。
- Provider、模型、Prompt 和 Schema 分别为 `deepseek`、`deepseek-v4-flash-vision-exp`、`teaching-v0.2+deepseek-json`、`teaching-lesson-v0.2`。
- 4 个章节、2 道互动题、来源引用和课程结构均有效；前述截断与缺失字段问题均未重现。

人工语义复核结果：标题、摘要、学习目标、MVP 核心假设、P0 范围、核心流程、P2 边界和非目标用户均与 PRD 一致；两道互动题的正确答案和解析也能由原文支持。该案例通过。两个受控真实教学案例（函数极限合成资料、MVP PRD）均已通过人工语义复核，但不外推为所有主题、资料格式或正式发布结论。

后续仍需在更多资料类型和主题上检查讲解是否忠实于资料、例子是否正确、互动题答案是否合理；继续保持单次、零自动重试和脱敏记录。
