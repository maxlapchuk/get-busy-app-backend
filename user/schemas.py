from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    first_name: str
    last_name: str
    password: str


class UserRead(UserBase):
    id: int
    first_name: str
    last_name: str

    class Config:
        from_attributes = True


class UserLogin(UserBase):
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
