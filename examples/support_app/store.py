"""Customer-scoped queries over imported UCI invoices and local tickets."""

import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

DEFAULT_CUSTOMER = "12347"
SOURCE = "UCI Online Retail (2010–2011), DOI: 10.24432/C5BW33"


def create_schema(db: sqlite3.Connection) -> None:
    db.executescript("""
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY, customer TEXT NOT NULL, invoice_date TEXT NOT NULL,
            country TEXT NOT NULL, record_type TEXT NOT NULL, line_total_gbp TEXT NOT NULL,
            line_count INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS orders_customer ON orders(customer, invoice_date);
        CREATE TABLE IF NOT EXISTS order_lines (
            source_row INTEGER PRIMARY KEY, order_id TEXT NOT NULL, stock_code TEXT NOT NULL,
            description TEXT NOT NULL, quantity INTEGER NOT NULL, unit_price_gbp TEXT NOT NULL,
            line_total_gbp TEXT NOT NULL, recorded_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS lines_order ON order_lines(order_id, source_row);
        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY, customer TEXT NOT NULL, order_id TEXT NOT NULL,
            issue TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(customer, order_id, issue)
        );
    """)


class Store:
    def __init__(self, path: Path, customer_id: str = DEFAULT_CUSTOMER):
        if not path.is_file():
            raise ValueError("Import the dataset first: python -m examples.support_app.import_data")
        self.path = path
        self.customer_id = customer_id.strip()
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM metadata WHERE key='import_complete'").fetchone():
                raise ValueError("Dataset import is incomplete; rerun the importer.")
            if not db.execute(
                "SELECT 1 FROM orders WHERE customer=?", (self.customer_id,)
            ).fetchone():
                raise ValueError("Customer ID not found in the imported historical dataset.")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def orders(self, offset: int = 0) -> dict:
        if offset < 0:
            return {"error": "Offset must be non-negative."}
        with self.connect() as db:
            count = db.execute(
                "SELECT count(*) FROM orders WHERE customer=?", (self.customer_id,)
            ).fetchone()[0]
            rows = db.execute(
                "SELECT id, invoice_date, record_type, line_total_gbp, line_count FROM orders "
                "WHERE customer=? ORDER BY invoice_date DESC, id LIMIT 10 OFFSET ?",
                (self.customer_id, offset),
            ).fetchall()
        return {
            "source": SOURCE,
            "historical": True,
            "customer_id": self.customer_id,
            "total_records": count,
            "orders": [dict(row) for row in rows],
            "next_offset": offset + len(rows) if offset + len(rows) < count else None,
            "amount_note": "GBP sum of recorded quantity × unit price; not proof of payment or refund.",
        }

    def order(self, order_id: str, offset: int = 0) -> dict:
        if offset < 0:
            return {"error": "Offset must be non-negative."}
        with self.connect() as db:
            row = db.execute(
                "SELECT id, invoice_date, country, record_type, line_total_gbp, line_count "
                "FROM orders WHERE id=? AND customer=?",
                (order_id.strip().upper(), self.customer_id),
            ).fetchone()
            if row is None:
                return {"error": "Order not found for the selected historical customer."}
            lines = db.execute(
                "SELECT stock_code, description, quantity, unit_price_gbp, line_total_gbp, recorded_at "
                "FROM order_lines WHERE order_id=? ORDER BY source_row LIMIT 25 OFFSET ?",
                (row["id"], offset),
            ).fetchall()
        return {
            **dict(row),
            "source": SOURCE,
            "historical": True,
            "currency": "GBP",
            "invoice_date_note": "Earliest recorded line timestamp; timezone unspecified. Each item retains its source timestamp.",
            "items": [dict(line) for line in lines],
            "next_offset": offset + len(lines) if offset + len(lines) < row["line_count"] else None,
            "shipping_status": None,
            "estimated_delivery": None,
            "amount_note": "Signed sum of recorded line amounts; no payment/refund confirmation.",
            "delivery_note": "Shipping and delivery dates are not supplied by this dataset.",
        }

    def create_ticket(self, order_id: str, issue: str) -> dict:
        order = self.order(order_id)
        issue = issue.strip()
        if "error" in order:
            return order
        if not 5 <= len(issue) <= 1000:
            return {"error": "Describe the issue in 5 to 1000 characters."}
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO tickets (id, customer, order_id, issue) VALUES (?, ?, ?, ?)",
                ("TKT-" + uuid4().hex, self.customer_id, order["id"], issue),
            )
            row = db.execute(
                "SELECT id, order_id, issue, status, created_at FROM tickets "
                "WHERE customer=? AND order_id=? AND issue=?",
                (self.customer_id, order["id"], issue),
            ).fetchone()
        return {
            "ticket": dict(row),
            "notice": "Saved locally for learning only; no external team was contacted.",
        }

    def tickets(self) -> list[dict]:
        with self.connect() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT id, order_id, issue, status, created_at FROM tickets "
                    "WHERE customer=? ORDER BY created_at, id",
                    (self.customer_id,),
                )
            ]


def decimal_text(value: Decimal) -> str:
    return format(value, "f")
