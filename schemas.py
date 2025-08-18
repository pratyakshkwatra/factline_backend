from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime 

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class RefreshToken(BaseModel):
    refresh_token: str

class UserOut(UserBase):
    id: int
    is_active: bool
    role: str

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None

class PostBase(BaseModel):
    title: str
    body: str

class PostCreate(PostBase):
    pass

class PostOut(PostBase):
    id: int
    created_at: datetime
    owner: UserOut  

    class Config:
        orm_mode = True
