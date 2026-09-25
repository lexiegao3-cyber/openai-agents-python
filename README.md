# Retail Support Agent

基于 OpenAI Agents Python SDK 的英文终端客服应用。通过工具查询 SQLite 中的真实公开历史交易，由 OpenAI 模型解释结果，并提供会话记忆和人工确认后创建本地练习工单的流程。

这是 [OpenAI Agents Python](https://github.com/openai/openai-agents-python) 的学习分支。客服代码位于 `examples/support_app/`；`src/agents/` 和其他示例保留上游 SDK 内容。本应用不是可直接上线的电商客服系统。

## 功能和边界

- 按客户分页列出历史发票，查询商品、数量、单价、金额与开票时间。
- 模型用英文回答，依据工具结果，不编造物流和预计送达时间。
- 按客户及会话名称保存聊天，支持继续对话或清空当前会话。
- 创建工单前显示具体内容，要求终端输入 `yes`；工单仅保存到本机。
- 支持不调用模型的离线数据查看与单元测试。

数据来自 [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail)，涵盖 2010-12-01 至 2011-12-09 的历史交易，币种 GBP。它不是实时订单库，没有物流、付款结算或商家现行政策。取消记录不能证明退款成功。政策文件是虚构练习政策，工单不会通知真实商家。

数据引用：Chen, D. (2015). *Online Retail*. UCI Machine Learning Repository. [DOI: 10.24432/C5BW33](https://doi.org/10.24432/C5BW33)，许可为 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。本应用将工作簿转换为按客户查询的 SQLite 表；转换细节见[应用说明](examples/support_app/README.md)。

## 安装与离线运行

需要 Python 3.10+、Git 和 uv。已克隆仓库的用户从现有目录开始，不必重复克隆。

```sh
git clone https://github.com/lexiegao3-cyber/retail-support-agent.git
cd retail-support-agent
uv sync --group dev
source .venv/bin/activate
uv pip install -r examples/support_app/requirements-data.txt
python -m examples.support_app.import_data
python -m examples.support_app --demo
```

导入器下载约 23 MB 的官方归档，复用已经完成的数据库，不覆盖订单和工单。后续 `uv sync` 可能移除导入专用依赖；需要再次导入时重新安装 `requirements-data.txt`。

## 启动英文客服

在同一个终端设置 `OPENAI_API_KEY`。macOS 默认 zsh 可使用隐藏输入，粘贴密钥后按回车：

```zsh
read -s 'OPENAI_API_KEY?OpenAI API Key: '
export OPENAI_API_KEY
printf '\n'
python -m examples.support_app
```

密钥不要写入代码或提交 Git。在线回答需要可用 API 额度；离线查看与单元测试不需要。在线模式会将聊天和工具结果发给 OpenAI。本应用关闭 tracing，但仍在本地保存对话。

默认匿名客户为 `12347`。可尝试：

```text
List my orders.
What products and quantities are in invoice 581180?
What is the total recorded amount in GBP?
Do you have a delivery date?
Create a support ticket about this invoice.
List my tickets.
```

确认工单时输入 `yes` 才保存，其他输入取消。`exit` 退出；`/new` 清空当前会话。继续命名会话：

```sh
python -m examples.support_app --customer 12347 --session learning
```

`--customer` 是本地学习选择器，不是身份认证。模型工具不能切换当前客户。

## 代码与学习路径

| 文件 | 内容 |
| --- | --- |
| `examples/support_app/__main__.py` | 异步终端循环、会话与命令行 |
| `examples/support_app/agent.py` | Agent 指令、工具、人工确认与并发锁 |
| `examples/support_app/store.py` | 客户范围内的查询、分页与工单持久化 |
| `examples/support_app/import_data.py` | 数据下载、校验与事务导入 |
| `examples/support_app/test_support.py` | 离线行为和边界测试 |
| `src/agents/` | 上游 SDK 实现 |

建议先离线查看，再运行模型对话，沿“用户输入 → Agent → 工具 → SQLite → 模型回答”读代码。`async def` 定义协程函数；`await` 等待可等待对象，在挂起时允许事件循环执行其他任务，并不自动让所有代码并行。

## 本地数据与验证

下载文件、数据库和聊天位于被 Git 忽略的 `.tmp/support-app/`。应用使用 `uci-retail.sqlite` 和 `uci-conversations.sqlite`，不读取旧模拟订单库。

```sh
python -m unittest examples.support_app.test_support -v
ruff check examples/support_app
ruff format --check examples/support_app
git diff --check
```

单元测试使用隔离的合成样本及脚本化模型，不验证真实 API 回答。开发流程见 [CONTRIBUTING.md](CONTRIBUTING.md)，代码助手规则见 [AGENTS.md](AGENTS.md)。

后续可扩展真实商家 API、登录认证、物流、知识库及客服后台；这些目前尚未实现。SDK 许可证见 [LICENSE](LICENSE)，数据使用前述独立许可。
