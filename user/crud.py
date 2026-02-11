from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import EmailStr
import os

from database import get_db
from .models import User
from .schemas import UserCreate
from .security import hash_password


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

load_dotenv()

ACCESS_SECRET_KEY = os.getenv("ACCESS_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    hashed = hash_password(user.password)
    db_user = User(
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        hashed_password=hashed
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_user_by_email(db: AsyncSession, email: EmailStr) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = jwt.decode(token, ACCESS_SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
