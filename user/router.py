from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta, datetime, timezone
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import selectinload

from .models import RefreshToken
from .schemas import UserCreate, UserRead, Token, UserLogin
from .crud import create_user, get_user_by_email, get_current_user
from .security import verify_password, create_access_token, \
    create_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES, hash_refresh_token
from database import get_db


router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@router.post("/register", response_model=UserRead)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await create_user(db, user)


@router.post("/login", response_model=Token)
async def login(login_info: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, login_info.email)
    if not user or not verify_password(login_info.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        {"sub": user.email},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    refresh_token = create_refresh_token()
    refresh_hash = hash_refresh_token(refresh_token)

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
    )
    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


@router.post("/refresh", response_model=Token)
async def refresh(refresh_token: str, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(refresh_token)

    refresh_token_in_db = await db.execute(
        select(RefreshToken)
        .options(selectinload(RefreshToken.user))
        .where(RefreshToken.token_hash == token_hash)
    )
    stored_token = refresh_token_in_db.scalar_one_or_none()

    if (
        not stored_token
        or stored_token.revoked_at
        or stored_token.expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    stored_token.revoked_at = datetime.now(timezone.utc)

    new_refresh_token = create_refresh_token()
    new_hash = hash_refresh_token(new_refresh_token)

    db.add(
        RefreshToken(
            user_id=stored_token.user_id,
            token_hash=new_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
    )

    access_token = create_access_token(
        {"sub": stored_token.user.email},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    await db.commit()

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
    }


@router.post("/logout")
async def logout(refresh_token: str, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(refresh_token)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored_token = result.scalar_one_or_none()

    if stored_token:
        stored_token.revoked_at = datetime.now(timezone.utc)
        await db.commit()

    return {"detail": "Logged out"}


@router.get("/me", response_model=UserRead)
async def me(user=Depends(get_current_user)):
    return user
