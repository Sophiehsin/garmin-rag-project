"""JWT auth + Google OAuth helpers (Task 4).

Flow:
  1. GET /auth/google  → redirect to Google consent screen
  2. GET /auth/callback → exchange code for Google token → upsert User → issue JWT
  3. Every protected endpoint: Authorization: Bearer <jwt>
     → get_current_user() decodes JWT → injects User into handler
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_db
from app.models.sql_models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT with user_id as subject.

    Default expiry: settings.jwt_expire_days (30 days).
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.jwt_expire_days)
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency — decode JWT, look up User, raise 401 if anything fails."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exc
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = db.exec(select(User).where(User.id == int(user_id))).first()
    if user is None:
        raise credentials_exc
    return user


# ---------------------------------------------------------------------------
# Google OAuth endpoints (mounted in main.py under /auth)
# ---------------------------------------------------------------------------

async def google_oauth_login() -> RedirectResponse:
    """GET /auth/google — redirect to Google OAuth2 consent screen."""
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(url=f"{_GOOGLE_AUTH_URL}?{query}")


async def google_oauth_callback(code: str, db: Session = Depends(get_db)) -> dict:
    """GET /auth/callback — exchange code → Google token → upsert User → issue JWT."""
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        google_token = token_resp.json().get("access_token")

        info_resp = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_token}"},
        )
        info_resp.raise_for_status()
        user_info = info_resp.json()

    email: str = user_info.get("email", "")
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    user = db.exec(select(User).where(User.email == email)).first()
    if user is None:
        user = User(email=email)
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}
