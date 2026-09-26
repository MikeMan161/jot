from pydantic import BaseModel, Field

class ParseRequest(BaseModel):
    # Bounded because this string goes straight into billable input tokens. 500
    # characters is far past any real "spent $40 on groceries yesterday" entry, so the
    # cap costs nothing to honest use while stopping a large body from being an
    # expensive request. Rejected by FastAPI as a 422 before Claude is ever called.
    text: str = Field(min_length=1, max_length=500)
    # The browser's local date, because the server's is UTC. Without it, anyone
    # entering "coffee today" after 8pm Eastern gets tomorrow's date. Optional so
    # a caller that omits it still works, just with the server's idea of today.
    #
    # Pattern-constrained because build_system_prompt interpolates this value into the
    # system prompt: an unvalidated string here is an injection point into Claude's
    # instructions, not just a bad date.
    today: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")

class ParsedTransaction(BaseModel):
    amount: str | None = None
    description: str | None = None
    merchant: str | None = None
    category_id: str | None = None
    transaction_date: str | None = None

class ParseResponse(BaseModel):
    transactions: list[ParsedTransaction]
