"""
Authentication dependency for FastAPI route protection. 
provides get_current_user dependency that validates JWT tokens
and returns the authenticated user for protected routes.
"""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from .auth import verify_token
from .database import get_db
from .models.models import Users

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)): 
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user_id: str = payload.get("sub")
    user = db.query(Users).filter(Users.id == user_id).first()
    if user is None:
        # 401, not 404. The token parsed but names a user who no longer exists, which
        # is a dead session rather than a missing resource — and the client can only
        # react correctly if it is told that. This is routine once demo accounts
        # exist: a purged demo user's token stays cryptographically valid until it
        # expires, and the frontend's AuthError path keys off 401 to clear the token
        # and send the visitor back to the landing page. On a 404 it silently renders
        # an empty screen instead.
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user