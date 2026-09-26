"""Registration, login, and throwaway demo accounts."""
import logging

from app.schemas.user import UserCreate, UserResponse, Token
from app.database import get_db
from app.models.models import Users
from app.auth import hash_password, create_access_token, verify_password
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.services.seeding import seed_default_buckets
from app.services.demo import create_demo_user, purge_expired_demo_users
from app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/auth/register", response_model=UserResponse) #endpoint for user registration
# Registration is open and /docs is public, so this is the gate on someone scripting
# accounts to get at the AI endpoint. `request` is required by slowapi, not by the body.
@limiter.limit("5/hour")
async def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(Users).filter(
        or_(Users.email == user.email, Users.username == user.username)
    ).first()
    if existing_user:
        if existing_user.email == user.email:
            raise HTTPException(status_code=409, detail="Email already registered")
        raise HTTPException(status_code=409, detail="Username already taken")
        
    new_user = Users(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password),
        currency=user.currency,
        monthly_income=user.monthly_income
    )
    try:
        db.add(new_user)
        db.flush()
        seed_default_buckets(db,new_user)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        constraint = getattr(e.orig.diag, "constraint_name", None)
        if constraint == "users_email_key":
            raise HTTPException(status_code=409, detail="Email already registered")
        if constraint == "users_username_key":
            raise HTTPException(status_code=409, detail="Username already taken")
        raise
    db.refresh(new_user)
    return new_user

@router.post("/auth/login", response_model=Token) #endpoint for user login
# Loose enough for someone fumbling their password, tight enough that the endpoint is
# not a credential-stuffing target.
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.email == form_data.username).first()
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")


@router.post("/auth/demo", response_model=Token)
# Each call creates an account and ~35 rows of sample data, so this is the gate on
# someone looping the demo button to fill the database.
@limiter.limit("5/hour")
async def start_demo(request: Request, db: Session = Depends(get_db)):
    """
    Create a throwaway account preloaded with sample data and return a token for it.

    There is no password involved. The account is created server-side and the endpoint
    hands back the same JWT that /auth/login would issue for it, so the browser is
    logged in by the existing token flow — nothing about session handling is special
    for demo users.
    """
    # Cleanup rides on the demo path so there is no scheduled job to run on Elastic
    # Beanstalk. It is committed separately and failure is swallowed: an expired
    # account that sticks around is a cosmetic problem, but a purge error that blocks
    # a judge from starting a demo is not.
    try:
        if purge_expired_demo_users(db):
            db.commit()
    except Exception:
        logger.exception("Demo cleanup failed; continuing with demo creation")
        db.rollback()

    try:
        user = create_demo_user(db)
        db.commit()
    except IntegrityError:
        # The random suffix collided with a live demo account, which is close enough
        # to impossible to be worth one retry rather than a loop.
        db.rollback()
        try:
            user = create_demo_user(db)
            db.commit()
        except IntegrityError:
            db.rollback()
            logger.exception("Demo user creation failed twice on a unique constraint")
            raise HTTPException(
                status_code=503,
                detail="Could not start a demo just now. Please try again.",
            )

    db.refresh(user)
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token, token_type="bearer")