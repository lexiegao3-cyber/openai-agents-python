"""Run with python -m examples.support_app."""

import argparse
import asyncio
import os
from pathlib import Path

from agents import RunConfig, Runner, SQLiteSession

from .agent import SupportContext, build_agent
from .store import DEFAULT_CUSTOMER, Store

DATA_DIR = Path(__file__).resolve().parents[2] / ".tmp" / "support-app"


async def confirm(preview: str) -> bool:
    print(f"\nCreate this LOCAL ticket? {preview}")
    answer = await asyncio.to_thread(lambda: input("Type yes to confirm; anything else cancels: "))
    return answer.strip().lower() == "yes"


async def main() -> None:
    parser = argparse.ArgumentParser(description="English customer support demo")
    parser.add_argument(
        "--session", default="default", help="Conversation name; reuse it to resume"
    )
    parser.add_argument(
        "--demo", action="store_true", help="Run local tools only, without an API key"
    )
    parser.add_argument(
        "--customer",
        default=DEFAULT_CUSTOMER,
        help="Historical anonymous customer ID (learning selector, not login)",
    )
    args = parser.parse_args()
    try:
        store = Store(DATA_DIR / "uci-retail.sqlite", args.customer)
    except (ValueError, OSError) as exc:
        print(str(exc))
        return
    if args.demo:
        print(
            "OFFLINE VIEW: real historical UCI invoices (2010–2011), no model calls or new tickets."
        )
        print(store.orders())
        print(Path(__file__).with_name("policies.md").read_text(encoding="utf-8"))
        print("Local tickets:", store.tickets())
        return
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY in this terminal, or use --demo for the offline walkthrough.")
        return
    session = SQLiteSession(
        f"uci:{store.customer_id}:{args.session}", DATA_DIR / "uci-conversations.sqlite"
    )
    context = SupportContext(store=store, confirm=confirm)
    agent = build_agent()
    print(
        f"UCI Online Retail — historical 2010–2011 data, customer {store.customer_id}, currency GBP."
    )
    print(
        "Not live orders. Shipping dates unavailable. Policies and new tickets are learning-only."
    )
    print("Example invoice IDs:", ", ".join(row["id"] for row in store.orders()["orders"][:3]))
    print(
        "English responses. History is saved locally. Type exit to leave or /new to clear this chat."
    )
    try:
        while True:
            message = (await asyncio.to_thread(lambda: input("\nYou: "))).strip()
            if message.lower() in {"exit", "quit"}:
                break
            if not message:
                continue
            if message == "/new":
                await session.clear_session()
                print("Conversation cleared. Orders and tickets are unchanged.")
                continue
            try:
                result = await Runner.run(
                    agent,
                    message,
                    context=context,
                    session=session,
                    run_config=RunConfig(tracing_disabled=True),
                    max_turns=8,
                )
                print(f"\nSupport: {result.final_output}")
            except Exception as exc:
                print(
                    f"Request failed ({type(exc).__name__}). Check your API access or connection."
                )
                print(
                    "A confirmed ticket may already exist. Use 'list my tickets' before retrying."
                )
    except EOFError:
        print("\nGoodbye.")
    finally:
        session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye.")
