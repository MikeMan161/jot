"""
Turns a line of free text into transaction drafts. Nothing here touches the
database — the drafts go back to the manual entry form and the user confirms
them, so a bad guess costs an edit rather than a bad row.
"""
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.models.models import Categories, Users
from app.schemas.ai import ParsedTransaction

load_dotenv(Path(__file__).parent.parent.parent / ".env")

MODEL = "claude-haiku-4-5-20251001"

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    """
    Built on first use rather than at import. Constructing the client without
    ANTHROPIC_API_KEY set raises, and doing that at import time takes down every
    route in the API, not just this one.
    """
    global _client
    if _client is None:
        # The SDK defaults to a 10-minute timeout and 2 retries, so one hung call
        # could hold a threadpool worker for half an hour. A parse that has not
        # come back in 20 seconds has already failed the user; the route catches
        # the timeout and returns the manual-entry fallback message.
        _client = anthropic.Anthropic(timeout=20.0, max_retries=1)
    return _client


# Forcing a tool call is what guarantees the shape. Asking for JSON in the prompt
# gets JSON most of the time and a friendly sentence wrapped around it the rest.
RECORD_TRANSACTIONS_TOOL = {
    "name": "record_transactions",
    "description": "Record every transaction described in the user's message.",
    "input_schema": {
        "type": "object",
        "properties": {
            "transactions": {
                "type": "array",
                "description": "One entry per transaction. Empty if the message describes none.",
                "items": {
                    "type": "object",
                    "properties": {
                        "amount": {
                            "type": "string",
                            "description": "Positive decimal, no currency symbol. e.g. '12.50'.",
                        },
                        "description": {
                            "type": "string",
                            "description": "What was bought, in the user's own words. Omit if the message only names a merchant.",
                        },
                        "merchant": {
                            "type": "string",
                            "description": "Where the money was spent. Omit if the message does not name one.",
                        },
                        "category_id": {
                            "type": "string",
                            "description": "The id of the closest matching category from the list in the system prompt. Pick the closest reasonable match rather than leaving this blank — a coffee shop belongs under a dining or food category if one exists, a gas station under transport. Omit only when the transaction fits two categories equally well, or when nothing in the list is related to it.",
                        },
                        "transaction_date": {
                            "type": "string",
                            "description": "YYYY-MM-DD. Resolve relative dates against today's date. Omit if the message gives no date.",
                        },
                    },
                },
            }
        },
        "required": ["transactions"],
    },
}


def build_system_prompt(categories: list[Categories], today: str) -> str:
    if categories:
        catalog = "\n".join(f"- {category.name} (id: {category.id})" for category in categories)
    else:
        catalog = "- (this user has no categories yet)"

    return (
        "You extract transactions from short, informal notes a person writes about "
        "money they just spent.\n\n"
        f"Today is {today}. Resolve relative dates such as 'yesterday' or 'last Friday' "
        "against it.\n\n"
        "The user's categories:\n"
        f"{catalog}\n\n"
        "Rules:\n"
        "- One entry per transaction. 'coffee 5 and gas 40' is two entries, not one.\n"
        "- Omit any merchant, description or date you are not confident about. A blank "
        "the user fills in beats a confident guess they do not notice.\n"
        "- Category is the exception: pick the closest reasonable match rather than "
        "leaving it blank. Reason from what the merchant sells — a coffee shop is "
        "dining, a supermarket is groceries, a gas station is transport. Omit it only "
        "when the purchase fits two categories equally well, or when nothing in the "
        "list is related to it.\n"
        "- Only ever use a category_id from the list above. Never invent one.\n"
        "- Amounts are positive decimals with no currency symbol.\n"
    )


def clean_row(raw: dict, valid_ids: set[str]) -> ParsedTransaction:
    """
    A hallucinated category_id would pass Pydantic and then 404 at save time
    against the ownership check in the transactions router, so anything not in
    this user's own categories is dropped back to uncategorized here.
    """
    category_id = raw.get("category_id")
    if category_id not in valid_ids:
        category_id = None

    return ParsedTransaction(
        amount=raw.get("amount"),
        description=raw.get("description"),
        merchant=raw.get("merchant"),
        category_id=category_id,
        transaction_date=raw.get("transaction_date"),
    )


def parse_transaction_with_claude(
    db: Session,
    current_user: Users,
    text: str,
    today: str | None = None,
) -> list[ParsedTransaction]:
    categories = db.query(Categories).filter(Categories.user_id == current_user.id).all()
    valid_ids = {str(category.id) for category in categories}

    if today is None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    response = get_client().messages.create(
        model=MODEL,
        max_tokens=1024,
        system=build_system_prompt(categories, today),
        tools=[RECORD_TRANSACTIONS_TOOL],
        tool_choice={"type": "tool", "name": RECORD_TRANSACTIONS_TOOL["name"]},
        messages=[{"role": "user", "content": text}],
    )

    # tool_choice forces the call, so this loop finds it on the first block in
    # practice. Falling through to an empty list keeps a surprise response from
    # becoming an exception the user sees.
    for block in response.content:
        if block.type == "tool_use":
            rows = block.input.get("transactions", [])
            return [clean_row(row, valid_ids) for row in rows]

    return []
