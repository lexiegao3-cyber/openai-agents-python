---
name: implementation-final-review
description: Optional focused review checklist for the customer support learning app.
---

# 客服应用复核清单

本文件替换原上游审查流程，只在明确选择使用时作为参考，不自动要求独立代理、状态文件、多轮审查或用户审批。当前项目规则以根目录 AGENTS.md 和 CONTRIBUTING.md 为准。

1. 根据实际差异确认改动范围，检查是否保留现有用户工作。
2. 涉及数据时检查客户隔离、金额精度、分页、事务和历史数据限制。
3. 涉及工单时检查具体内容预览、明确确认、并发串行化和重复处理。
4. 涉及会话时检查客户隔离、持久化和清空范围。
5. 检查差异中是否含密钥、数据库或对话。
6. 按改动范围使用 CONTRIBUTING.md 的检查命令，报告实际结果和未验证部分。

文档修改核对事实、命令、链接及差异即可。无需运行旧 references/ 和 scripts/ 的审查协议；这些文件仅保留用于现有辅助工具兼容。
