# Customer Support Agent — real historical orders

An English-speaking learning application backed by **UCI Online Retail**, a real public transaction dataset from **2010-12-01 to 2011-12-09**. These are historical invoices, not live shopping orders. The application queries an imported SQLite database; OpenAI explains tool results. Fictional seeded orders are no longer used.

## Why this dataset

UCI Online Retail has product descriptions, quantities, unit prices in pounds sterling (GBP), invoice dates, anonymous customer IDs and cancellation records. This makes it useful for product, quantity, amount and order-list questions. It does **not** contain shipping status, tracking numbers, delivery dates, current stock, payment settlement or merchant policies. Those facts must not be invented. Olist is another public historical dataset worth considering for a future delivery-analysis project; this version prioritizes item descriptions and transaction detail.

Source: [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail). Citation: Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. [DOI: 10.24432/C5BW33](https://doi.org/10.24432/C5BW33). License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). This application transforms the workbook into customer-scoped SQLite tables; it is not endorsed by UCI or the original retailer.

## Initial data setup

From the repository root with `.venv` active:

```sh
uv pip install -r examples/support_app/requirements-data.txt
python -m examples.support_app.import_data
```

The importer downloads the official archive (~23 MB) and reads its `Online Retail.xlsx` member. An already downloaded official workbook can be supplied with `--xlsx /path/to/Online\ Retail.xlsx`. The importer records file SHA-256 hashes and import counts in SQLite metadata. A completed import is reused without overwriting orders or tickets. `openpyxl` is needed only for importing the workbook; reinstall the importer requirements if a later `uv sync` removes it.

Rows without CustomerID cannot be assigned to a customer and are excluded. Invalid core fields, zero quantities and negative prices are excluded and counted. Original line repetitions are retained. Negative quantities and invoices prefixed `C` are preserved; `C` means a cancellation record, not a verified refund. Amounts are calculated using decimal arithmetic as signed quantity × unit price, with no invented shipping charges or tax. When line timestamps differ, the invoice date is the earliest timestamp; original line timestamps are retained. Invoice ownership/country conflicts abort the transaction rather than silently combining customers.

## Start chatting

Set `OPENAI_API_KEY` in your terminal, then:

```sh
python -m examples.support_app
```

The default anonymous historical customer is `12347`, with seven invoices. For example, invoice `581180` has 11 recorded lines totaling GBP 224.82; quantities can exceed one per line. The startup screen displays invoice IDs from the imported dataset. Start with:

```text
List my orders.
What products and quantities are in my most recent invoice?
What is the total recorded amount in GBP?
When was that invoice issued?
Do you have a delivery date?
```

Use the invoice IDs printed by the application, not the old `ORD-1001` examples. To inspect another anonymous public-data customer, use `--customer CUSTOMER_ID`. This is a **local learning selector, not authentication**. The model cannot change the selected customer through its tools. Invoice and item lists are paginated; the assistant can follow `next_offset` to get more.

## Policies and tickets

`policies.md` is still a fictional training policy, not a real policy from the historical merchant. The assistant must identify it as such. Historical invoices do not establish current refund/return eligibility. New tickets are practice records saved only on your computer: no real support team is contacted, and no refund, cancellation or payment is executed.

Ask to create a ticket, then type `yes` at the exact ticket preview to save it. Anything else cancels. Confirmations are serialized. Identical customer/order/issue requests reuse the existing ticket. Ask `List my tickets` to inspect status.

## Memory and local files

`--session NAME` resumes a named conversation for the selected historical customer. `/new` clears only that conversation; `exit` quits. Data is stored in `.tmp/support-app/uci-retail.sqlite`, and new chats in `uci-conversations.sqlite`. These are ignored by Git. The old `support.sqlite` and `conversations.sqlite` are preserved, but no longer opened by this application, so previous fictional facts cannot contaminate new chat history.

The source workbook is under `.tmp/support-app/source/`. Database files and histories are plain local files. Chat messages and tool results are sent to OpenAI for live responses; tracing is disabled and the application does not save API keys. Do not add real private customer data to this public-data learning demo.

## Offline checks

```sh
python -m examples.support_app --demo
python -m unittest examples.support_app.test_support -v
```

`--demo` now displays actual imported historical records without a model call. Unit tests use clearly synthetic isolated fixtures and scripted model replies to check import accounting, decimal amounts, cancellation records, customer scoping, lists, confirmation, persistence and memory. They do not validate live model wording.

## Reading order

1. `__main__.py`: async chat, session scoping and CLI.
2. `agent.py`: instructions, five tools and manual confirmation.
3. `store.py`: scoped queries, pagination and ticket persistence.
4. `import_data.py`: source download, validation and transactional import.
5. `test_support.py`: offline workflow and data-boundary tests.

## Import verified on this machine

Official workbook SHA-256: `43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d`. Read 541,909 source rows; imported 406,829 lines across 22,190 invoices and 4,372 customers. Excluded 135,080 rows with no customer ID. All remaining rows passed the current field checks. Raw quantities and repeated rows are retained, so these counts are not a deduplicated sales-analysis dataset.
