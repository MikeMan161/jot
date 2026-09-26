"""
Entry point for the Financial Dashboard API. Registers all routers and configures
CORS from the CORS_ORIGINS environment variable, a comma-separated list of allowed
frontend origins. Exposes /health for Elastic Beanstalk, which verifies the
database connection rather than just confirming the process is alive.
"""

from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from slowapi.errors import RateLimitExceeded
from app.database import get_db
from dotenv import load_dotenv
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, users, buckets, categories, transactions, savings_goals, debts, income, ai
from app.limiter import limiter
import os

load_dotenv(Path(__file__).parent.parent / ".env")

app = FastAPI(
    title="Jot",
    description="AI-powered personal finance tracker",
    version="0.1.0"
)

# slowapi's decorators look the limiter up on app.state at request time, so this
# assignment is what makes every @limiter.limit(...) in the routers actually fire.
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    slowapi ships its own handler, but it returns {"error": ...}. Every error message
    the frontend renders goes through extractDetail in src/api/auth.ts, which reads
    "detail" — so this returns the shape the client already knows how to display.
    """
    # Deliberately does not promise a wait time: this one handler covers limits with
    # per-minute and per-hour windows, and "try again in a minute" is wrong for the
    # hourly ones.
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please wait a bit and try again."},
    )

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(buckets.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(savings_goals.router)
app.include_router(debts.router)
app.include_router(income.router)
app.include_router(ai.router)

cors_origins = os.getenv("CORS_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Financial Dashboard API is running"}

@app.get("/health")
async def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
