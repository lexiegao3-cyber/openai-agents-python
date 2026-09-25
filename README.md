# Retail Support Agent

An English-speaking terminal customer support application built with the OpenAI Agents Python SDK. It queries real public historical transactions in SQLite through tools, uses an OpenAI model to explain the results, and supports conversation memory and local practice tickets with human confirmation.

This is a learning fork of [OpenAI Agents Python](https://github.com/openai/openai-agents-python). The support application lives in `examples/support_app/`; `src/agents/` and other examples retain the upstream SDK implementation. This application is not a production-ready commerce support system.

## Features and limitations

- List a selected customer's historical invoices with pagination, and look up products, quantities, unit prices, amounts, and invoice dates.
- Respond in English using tool results, without inventing shipping status or delivery estimates.
- Save conversations by customer and session name, resume a conversation, or clear the current session.
- Preview a ticket and require `yes` in the terminal before saving it locally.
- View imported data and run unit tests without calling a model.

The data comes from [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail), covering historical transactions from 2010-12-01 to 2011-12-09 in GBP. It is not a live order database and does not include shipping, payment settlement, or current merchant policies. Cancellation records do not prove that a refund was completed. The policy file contains fictional training policies, and tickets do not notify a real merchant.

Dataset citation: Chen, D. (2015). *Online Retail*. UCI Machine Learning Repository. [DOI: 10.24432/C5BW33](https://doi.org/10.24432/C5BW33). Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The application transforms the workbook into customer-scoped SQLite tables; see the [application guide](examples/support_app/README.md) for import details.

## Installation and offline walkthrough

Requirements: Python 3.10+, Git, and uv. If you already cloned the repository, start from your existing directory and skip the first two commands.

```sh
git clone https://github.com/lexiegao3-cyber/retail-support-agent.git
cd retail-support-agent
uv sync --group dev
source .venv/bin/activate
uv pip install -r examples/support_app/requirements-data.txt
python -m examples.support_app.import_data
python -m examples.support_app --demo
```

The importer downloads the official archive, approximately 23 MB. It reuses a completed database without overwriting existing invoices or tickets. A later `uv sync` may remove import-only dependencies; reinstall `requirements-data.txt` before importing again if needed.

## Start the support agent

Set `OPENAI_API_KEY` in the same terminal. In the default macOS zsh shell, use the following hidden-input prompt, paste your key, and press Enter:

```zsh
read -s 'OPENAI_API_KEY?OpenAI API Key: '
export OPENAI_API_KEY
printf '\n'
python -m examples.support_app
```

Do not put the key in source code or commit it to Git. Live responses require available OpenAI API credit or quota; offline viewing and unit tests do not. Live mode sends chat messages and tool results to OpenAI. Tracing is disabled, but conversations are still stored locally.

The default anonymous customer is `12347`. Try these prompts:

```text
List my orders.
What products and quantities are in invoice 581180?
What is the total recorded amount in GBP?
Do you have a delivery date?
Create a support ticket about this invoice.
List my tickets.
```

At the ticket confirmation prompt, type `yes` to save; any other input cancels. Type `exit` to quit or `/new` to clear the current conversation. To resume a named session:

```sh
python -m examples.support_app --customer 12347 --session learning
```

`--customer` is a local learning selector, not authentication. Model tools cannot switch the selected customer.

## Code structure and learning path

| File | Purpose |
| --- | --- |
| `examples/support_app/__main__.py` | Async terminal loop, sessions, and CLI |
| `examples/support_app/agent.py` | Agent instructions, tools, human confirmation, and concurrency lock |
| `examples/support_app/store.py` | Customer-scoped queries, pagination, and ticket persistence |
| `examples/support_app/import_data.py` | Data download, validation, and transactional import |
| `examples/support_app/test_support.py` | Offline behavior and boundary tests |
| `src/agents/` | Upstream SDK implementation |

Start with the offline walkthrough, then run a model conversation and follow the flow: user input → agent → tool → SQLite → model response. `async def` defines a coroutine function. `await` waits for an awaitable and, when suspended, allows the event loop to run other tasks; it does not automatically make all code run concurrently.

## Local data and verification

Downloads, databases, and conversations are stored in the Git-ignored `.tmp/support-app/` directory. The application uses `uci-retail.sqlite` and `uci-conversations.sqlite`; it does not read the old simulated-order database.

```sh
python -m unittest examples.support_app.test_support -v
ruff check examples/support_app
ruff format --check examples/support_app
git diff --check
```

Unit tests use isolated synthetic fixtures and scripted model responses. They do not validate live API responses. See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow and [AGENTS.md](AGENTS.md) for coding-agent guidance.

Future extensions could include authorized merchant APIs, authentication, shipping integrations, a knowledge base, and a support dashboard. These features are not implemented. The SDK license is in [LICENSE](LICENSE); the dataset has the separate license noted above.
