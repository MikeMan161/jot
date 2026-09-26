"""Free-text transaction parsing. Returns drafts for the user to confirm in a manual entry window. Nothing is submitted here."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from app.schemas.ai import ParseRequest, ParseResponse
from app.services.ai import parse_transaction_with_claude
from app.services.usage import record_ai_call
from app.models.models import Users
from app.dependencies import get_current_user
from app.database import get_db
from app.limiter import limiter, user_or_ip

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai",
    tags=["ai"],
    responses={404: {"description": "Not Found"}}
)

@router.post("/parse", response_model=ParseResponse)
# Keyed by user id rather than IP: judges on shared venue wifi would otherwise
# throttle each other. `request` is in the signature because slowapi reads the key
# off it — it is unused by the handler body.
@limiter.limit("10/minute", key_func=user_or_ip)
async def parse_transaction(
    request: Request,
    payload: ParseRequest,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count, limit = record_ai_call(db, current_user)
    if count > limit:
        # Coach, not judge — and it points at the exit that still works.
        raise HTTPException(
            status_code=429,
            detail="You've hit today's limit for AI entry. Manual entry still works, and the limit resets tomorrow."
        )

    try:
        # parse_transaction_with_claude is fully synchronous: a blocking psycopg2 query
        # followed by a blocking HTTP call to Anthropic. Awaiting it directly in an
        # async handler would run it on the event loop and stall every other request in
        # the worker for its whole duration, /health included. gunicorn runs one worker,
        # so that is the entire API. run_in_threadpool moves it off the loop.
        transactions = await run_in_threadpool(
            parse_transaction_with_claude, db, current_user, payload.text, payload.today
        )
    except Exception:
        # The SDK's exception text can carry request ids and key fragments, so it
        # goes to the log rather than to the browser.
        logger.exception("Transaction parse failed")
        raise HTTPException(
            status_code=502,
            detail="Could not read that one. Try rewording it, or use manual entry."
        )
    return ParseResponse(transactions=transactions)
