from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime
from models.post_model import AnalysisStatus 


class UserBase(BaseModel):
    email: EmailStr

class UserOut(UserBase):
    id: int
    is_active: bool
    role: str

    class Config:
        orm_mode = True


class PostBase(BaseModel):
    title: str
    body: str

class PostCreate(PostBase):
    pass

class PostOut(PostBase):
    id: int
    created_at: datetime
    owner: UserOut

    
    analysis_status: AnalysisStatus
    analysis: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True
