"""
Pydantic schemas for user-related API operations. Splitting into UserCreate,
UserResponse, and UserInDB ensures the hashed password is never returned in API
responses while still having a typed model for internal authentication logic.
Token holds the JWT shape returned by the login endpoint. CurrencyUpdate validates
against pycountry's ISO 4217 list instead of a hand-typed set of codes, so the
accepted currencies stay correct as the standard changes.
"""
from pydantic import BaseModel, EmailStr, field_validator, Field
from uuid import UUID
from datetime import datetime
from app.auth import hash_password
import pycountry

BCRYPT_MAX_PASSWORD_BYTES = 72

def _validate_currency_code(value: str) -> str:
    code = value.upper()
    if pycountry.currencies.get(alpha_3=code) is None:
        raise ValueError(f"'{value}' is not a valid ISO 4217 currency code")
    return code

def _validate_password_length(value: str) -> str:
    # bcrypt ignores everything past 72 bytes, so a longer password would be
    # silently truncated before hashing. Measured in bytes, not characters:
    # non-ASCII characters encode to more than one byte each.
    if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must be at most {BCRYPT_MAX_PASSWORD_BYTES} bytes; "
            "accented and non-Latin characters count as more than one byte"
        )
    return value

class UserCreate(BaseModel):
    username: str = Field(min_length=3)
    email: EmailStr
    password: str = Field(min_length=8)
    currency: str = "USD"
    monthly_income: float = Field(ge=0)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return _validate_currency_code(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password_length(value)

class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    username: str
    email: EmailStr
    created_at: datetime
    currency: str
    monthly_income: float
    # Exposed so the client can show the "this resets in a couple of hours" banner and
    # steer demo visitors toward signing up. Not a secret — the visitor already knows.
    is_demo: bool

class UserInDB(UserResponse):

    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class CurrencyUpdate(BaseModel):
    currency: str

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return _validate_currency_code(value)

class CurrencyInfo(BaseModel):
    code: str
    name: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _validate_password_length(value)

class MessageResponse(BaseModel):
    message: str

class UserUpdateIncome(BaseModel):
    monthly_income: float = Field(ge=0)


    