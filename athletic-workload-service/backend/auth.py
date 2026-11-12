
import os
from uuid import UUID

import httpx
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {token}"
                }
            )

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable"
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token"
        )

    user = response.json()

    try:
        user_id = UUID(user["id"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid user identity"
        )

    return {
        "id": user_id,
        "email": user.get("email")
    }
