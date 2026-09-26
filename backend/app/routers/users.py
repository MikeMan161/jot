"""Endpoints for reading and updating the authenticated user's profile and currency."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import pycountry
from app.database import get_db
from app.dependencies import get_current_user
from app.models.models import Users
from app.schemas.user import UserResponse, UserInDB, Token, CurrencyUpdate, CurrencyInfo, PasswordChange, MessageResponse, UserUpdateIncome
from app.auth import hash_password, verify_password

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

@router.get("/me", response_model=UserResponse)
async def get_user_me(current_user: Users = Depends(get_current_user)):
    return current_user

#revisit this when front end is completed to sharpen down ISO list.
@router.get("/currencies", response_model=list[CurrencyInfo])
async def list_currencies():
    """Returns the full ISO 4217 currency list from pycountry for populating a currency picker."""
    currencies = [
        CurrencyInfo(code=currency.alpha_3, name=currency.name)
        for currency in pycountry.currencies
    ]
    return sorted(currencies, key=lambda c: c.name)

@router.patch("/me/currency", response_model=UserResponse)
async def update_currency(
    payload: CurrencyUpdate,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.currency = payload.currency
    db.commit()
    db.refresh(current_user)
    return current_user

@router.patch("/me/password", response_model=MessageResponse)
async def change_password(
    payload: PasswordChange,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # A demo account has no password anyone knows — it was created with a random secret
    # that is never stored. Letting a visitor set one would turn a throwaway account
    # into a real login that then gets deleted out from under them two hours later.
    if current_user.is_demo:
        raise HTTPException(
            status_code=403,
            detail="Demo accounts can't change their password. Sign up for a free account to keep your data.",
        )

    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Current Password is incorrect")

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated successfully"}

@router.patch("/me/monthly_income", response_model=UserResponse)
async def change_monthly_income(
    payload: UserUpdateIncome,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.monthly_income = payload.monthly_income
    db.commit()
    db.refresh(current_user)
    return current_user
