# 学习资料分卷

这里保存已导入资料库的安全分卷，方便协作者在 GitHub 上共同使用和审阅。

## 文件来源

- `Calculus.pdf`：共 16 卷，覆盖第 1–2308 页。
- `An Introduction to Linear Algebra.pdf`：共 6 卷，覆盖第 1–587 页。

## 拆分规则

- PDF 只在页面边界拆分，不截断页面；分卷按原页码顺序命名。
- 每个分卷小于 20 MB，避免 GitHub 单文件限制。
- PDF 分卷由 `pypdf` 重新写出，页面顺序和页面内容保持；PDF 文件不能通过直接拼接二进制恢复为原始单文件。
- Markdown/TXT 若日后加入仓库，会优先按段落和行边界拆分，并保持 UTF-8 内容可按顺序拼接恢复。

## 版权提醒

上传到公共 GitHub 仓库前，请确认你拥有这些资料的再分发权限。特别是 `An Introduction to Linear Algebra.pdf` 原文件标注了 “All rights reserved”；如果没有公开分发授权，应将仓库设为私有或不要提交该资料。
