"""Offline checks: python -m unittest examples.support_app.test_support -v."""

import asyncio
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from agents import RunConfig, Runner, SQLiteSession
from agents.testing import ScriptedModel, assistant_message, function_call

from .agent import SupportContext, build_agent
from .import_data import import_rows
from .store import Store


class SupportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        import_rows(
            [
                (
                    "ORD-1001",
                    "LAMP",
                    "Desk lamp",
                    2,
                    datetime(2011, 1, 1),
                    2.55,
                    12347,
                    "United Kingdom",
                ),
                (
                    "ORD-1002",
                    "BOOK",
                    "Notebook",
                    3,
                    datetime(2011, 1, 2),
                    1.2,
                    12347,
                    "United Kingdom",
                ),
                (
                    "ORD-2001",
                    "BAG",
                    "Backpack",
                    1,
                    datetime(2011, 1, 3),
                    5,
                    12348,
                    "United Kingdom",
                ),
            ],
            self.path / "support.sqlite",
            {"source": "synthetic test fixture only"},
        )
        self.store = Store(self.path / "support.sqlite")

    def tearDown(self):
        self.temp.cleanup()

    async def test_order_scope_and_ticket_persistence(self):
        self.assertEqual(self.store.order(" ord-1001 ")["record_type"], "purchase_record")
        self.assertEqual(self.store.order("ORD-1001")["line_total_gbp"], "5.10")
        self.assertEqual(self.store.order("ORD-1001")["items"][0]["quantity"], 2)
        self.assertIsNone(self.store.order("ORD-1001")["shipping_status"])
        self.assertIn("error", self.store.order("ORD-2001"))
        self.assertIn("error", self.store.order("' OR 1=1 --"))
        self.assertIn("error", self.store.create_ticket("ORD-2001", "Where is my order?"))
        ticket = self.store.create_ticket("ORD-1001", "The lamp arrived damaged.")
        reopened = Store(self.path / "support.sqlite")
        repeated = reopened.create_ticket("ORD-1001", "The lamp arrived damaged.")
        self.assertEqual(ticket["ticket"]["id"], repeated["ticket"]["id"])
        self.assertEqual(len(reopened.tickets()), 1)
        self.assertEqual(reopened.tickets()[0]["status"], "open")

    async def exercise_ticket(self, approved):
        previews = []

        async def confirm(preview):
            previews.append(preview)
            return approved

        model = ScriptedModel(
            [
                [
                    function_call(
                        "create_support_ticket",
                        {"order_id": "ORD-1001", "issue": "The lamp arrived damaged."},
                        call_id="ticket-1",
                    )
                ],
                [assistant_message("Finished checking your request.")],
            ]
        )
        agent = build_agent()
        agent.model = model
        await Runner.run(
            agent,
            "Please create a ticket.",
            context=SupportContext(self.store, confirm),
            run_config=RunConfig(tracing_disabled=True),
        )
        model.assert_complete()
        self.assertEqual(len(previews), 1)
        self.assertIn("ORD-1001", previews[0])
        self.assertEqual(len(self.store.tickets()), int(approved))
        outputs = [x for x in model.last_call.input if x.get("type") == "function_call_output"]
        self.assertEqual(len(outputs), 1)
        self.assertIn("Saved locally" if approved else "cancelled", str(outputs[0]))

    async def test_approved_ticket_through_sdk(self):
        await self.exercise_ticket(True)

    async def test_rejected_ticket_through_sdk(self):
        await self.exercise_ticket(False)

    async def test_order_and_policy_tools(self):
        async def refuse(preview):
            self.fail("Read-only tools must not request confirmation")

        model = ScriptedModel(
            [
                [function_call("lookup_order", {"order_id": "ORD-1001"}, call_id="order-1")],
                [function_call("read_policies", {}, call_id="policy-1")],
                [assistant_message("According to policies.md, staff must review returns.")],
            ]
        )
        agent = build_agent()
        agent.model = model
        await Runner.run(
            agent,
            "Can I return ORD-1001?",
            context=SupportContext(self.store, refuse),
            run_config=RunConfig(tracing_disabled=True),
        )
        model.assert_complete()
        outputs = str([x for x in model.last_call.input if x.get("type") == "function_call_output"])
        self.assertIn("Desk lamp", outputs)
        self.assertIn("policies.md", outputs)
        self.assertIn("30 days", outputs)

    async def test_conversation_resume_and_clear(self):
        async def refuse(preview):
            return False

        path = self.path / "conversations.sqlite"
        session = SQLiteSession("customer:one", path)
        agent = build_agent()
        agent.model = ScriptedModel([[assistant_message("Your order is ORD-1001.")]])
        try:
            await Runner.run(
                agent,
                "Remember ORD-1001.",
                session=session,
                context=SupportContext(self.store, refuse),
                run_config=RunConfig(tracing_disabled=True),
            )
        finally:
            session.close()
        session = SQLiteSession("customer:one", path)
        other = SQLiteSession("customer:two", path)
        model = ScriptedModel([[assistant_message("You mentioned ORD-1001.")]])
        agent.model = model
        try:
            await Runner.run(
                agent,
                "Which order?",
                session=session,
                context=SupportContext(self.store, refuse),
                run_config=RunConfig(tracing_disabled=True),
            )
            self.assertIn("ORD-1001", str(model.last_call.input))
            self.assertEqual(await other.get_items(), [])
            await session.clear_session()
            self.assertEqual(await session.get_items(), [])
        finally:
            session.close()
            other.close()

    async def test_concurrent_ticket_confirmations_are_serial(self):
        active = 0
        peak = 0
        previews = []

        async def confirm(preview):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            order_id = json.loads(preview)["order_id"]
            previews.append(order_id)
            await asyncio.sleep(0.01)
            active -= 1
            return order_id == "ORD-1002"

        model = ScriptedModel(
            [
                [
                    function_call(
                        "create_support_ticket",
                        {"order_id": "ORD-1001", "issue": "Damaged lamp."},
                        call_id="first",
                    ),
                    function_call(
                        "create_support_ticket",
                        {"order_id": "ORD-1002", "issue": "Late notebook."},
                        call_id="second",
                    ),
                ],
                [assistant_message("Only your approved ticket was saved locally.")],
            ]
        )
        agent = build_agent()
        agent.model = model
        await Runner.run(
            agent,
            "Create two tickets.",
            context=SupportContext(self.store, confirm),
            run_config=RunConfig(tracing_disabled=True),
        )
        model.assert_complete()
        self.assertEqual(peak, 1)
        self.assertCountEqual(previews, ["ORD-1001", "ORD-1002"])
        self.assertEqual([t["order_id"] for t in self.store.tickets()], ["ORD-1002"])

    async def test_customer_listing_and_pagination(self):
        listing = self.store.orders()
        self.assertEqual(listing["total_records"], 2)
        self.assertEqual({x["id"] for x in listing["orders"]}, {"ORD-1001", "ORD-1002"})
        other = Store(self.path / "support.sqlite", "12348")
        self.assertIn("error", other.order("ORD-1001"))
        self.assertEqual(other.orders()["total_records"], 1)
        self.assertIn("error", self.store.orders(-1))
        self.assertIn("error", self.store.order("ORD-1001", -1))

    async def test_import_cancellations_missing_customers_and_duplicate_rows(self):
        path = self.path / "import.sqlite"
        row = ("900001", "A", "Item A", 2, datetime(2011, 1, 1), 1.25, 12347, "UK")
        report = import_rows(
            [
                row,
                row,
                ("C900002", "A", "Item A", -2, datetime(2011, 1, 2), 1.25, 12347, "UK"),
                ("900003", "A", "Item A", 1, datetime(2011, 1, 3), 1.25, None, "UK"),
            ],
            path,
            {"source": "synthetic fixture"},
        )
        self.assertEqual(report["imported_lines"], 3)
        self.assertEqual(report["excluded_missing_customer"], 1)
        store = Store(path)
        self.assertEqual(store.order("900001")["line_total_gbp"], "5.00")
        self.assertEqual(store.order("900001")["line_count"], 2)
        cancellation = store.order("c900002")
        self.assertEqual(cancellation["record_type"], "cancellation_record")
        self.assertEqual(cancellation["line_total_gbp"], "-2.50")
        ticket = store.create_ticket("900001", "Learning request")
        with self.assertRaises(ValueError):
            import_rows([row], path, {})
        self.assertEqual(store.tickets()[0]["id"], ticket["ticket"]["id"])

    async def test_inconsistent_invoice_rolls_back(self):
        path = self.path / "rollback.sqlite"
        with self.assertRaises(ValueError):
            import_rows(
                [
                    ("900001", "A", "Item A", 1, datetime(2011, 1, 1), 2, 12347, "UK"),
                    ("900001", "B", "Item B", 1, datetime(2011, 1, 1), 3, 12348, "UK"),
                ],
                path,
                {},
            )
        import sqlite3

        with sqlite3.connect(path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM order_lines").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM metadata").fetchone()[0], 0)

    async def test_order_list_tool_through_sdk(self):
        async def refuse(preview):
            self.fail("Listing must not request confirmation")

        model = ScriptedModel(
            [
                [function_call("list_orders", {"offset": 0}, call_id="list-1")],
                [assistant_message("These are historical invoices from 2011.")],
            ]
        )
        agent = build_agent()
        agent.model = model
        await Runner.run(
            agent,
            "List my orders",
            context=SupportContext(self.store, refuse),
            run_config=RunConfig(tracing_disabled=True),
        )
        model.assert_complete()
        outputs = str([x for x in model.last_call.input if x.get("type") == "function_call_output"])
        self.assertIn("ORD-1001", outputs)
        self.assertNotIn("ORD-2001", outputs)
        self.assertIn("GBP", outputs)

    async def test_item_pagination_and_source_times(self):
        path = self.path / "pages.sqlite"
        rows = [
            ("900010", f"SKU-{i}", f"Fixture {i}", 1, datetime(2011, 1, 1, 12, i), 0.1, 12347, "UK")
            for i in range(27)
        ]
        import_rows(rows, path, {"source": "synthetic fixture"})
        store = Store(path)
        first = store.order("900010")
        second = store.order("900010", first["next_offset"])
        self.assertEqual(len(first["items"]), 25)
        self.assertEqual(len(second["items"]), 2)
        self.assertIsNone(second["next_offset"])
        self.assertEqual(first["line_total_gbp"], "2.7")
        self.assertEqual(first["invoice_date"], "2011-01-01T12:00:00")
        self.assertEqual(second["items"][-1]["recorded_at"], "2011-01-01T12:26:00")
