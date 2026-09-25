# 客服应用开发说明

本分支以 `examples/support_app/` 为核心，日常开发遵循本文件与 [AGENTS.md](AGENTS.md)，不继承上游的强制多阶段审查和发布流程。

## 开发步骤

1. 按 [README.md](README.md) 准备环境，激活 `.venv`。
2. 明确用户行为与数据边界，阅读现有代码和差异。
3. 在对应应用模块中实现修改，为行为变更补充回归测试。
4. 执行相关检查，复核差异和说明文档。
5. 按用户授权提交或推送，报告实际验证结果。

## 应用检查

```sh
python -m unittest examples.support_app.test_support -v
ruff check examples/support_app
ruff format --check examples/support_app
git diff --check
```

离线测试不需要完整数据或 API Key。导入数据后可运行 `python -m examples.support_app --demo` 验证本地查询。在线交互使用用户终端中的密钥；没有执行时注明“在线未验证”。格式修复可用 `ruff format examples/support_app`，然后复查差异。

## SDK 修改

先运行受影响测试，较大修改再运行：

```sh
make format-check
make lint
make typecheck
make tests
```

需要完整可选依赖时使用 `make sync`；之后如需导入数据，重新安装 `examples/support_app/requirements-data.txt`。环境权限导致的失败应明确记录，不应通过删除测试掩盖。

## 复核重点

检查客户隔离、分页、十进制金额、取消记录解释、工单确认与去重、导入回滚及会话持久化。新政策必须标明是否为练习政策；不能以历史数据承诺实时服务。

文档修改核对事实、链接、命令和差异即可，不要求完整 SDK 测试、固定审查轮数、状态文件或 PR 草稿。上游 `.agents/` 辅助脚本保留用于工具链兼容，不自动触发旧流程。

## 版本控制

仅提交源码、说明和必要配置。密钥、下载数据、数据库和聊天记录不提交；公开数据保留来源及许可。推送须在用户授权范围内进行。SDK 的安全报告说明保留在 [SECURITY.md](SECURITY.md)，不要在公开 issue 中发布密钥或未披露漏洞。
