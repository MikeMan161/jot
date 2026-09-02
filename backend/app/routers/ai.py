"""Free-text transaction parsing. Returns drafts for the user to confirm in a manual entry window. Nothing is submitted here."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.ai import ParseRequest, ParseResponse
from app.services.ai import parse_transaction_with_claude
from app.models.models import Users
from app.dependencies import get_current_user
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai",
    tags=["ai"],
    responses={404: {"description": "Not Found"}}
)

@router.post("/parse", response_model=ParseResponse)
async def parse_transaction(
    payload: ParseRequest,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        transactions = parse_transaction_with_claude(db, current_user, payload.text, payload.today)
    except Exception:
        # The SDK's exception text can carry request ids and key fragments, so it
        # goes to the log rather than to the browser.
        logger.exception("Transaction parse failed")
        raise HTTPException(
            status_code=502,
            detail="Could not read that one. Try rewording it, or use manual entry."
        )
    return ParseResponse(transactions=transactions)