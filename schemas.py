from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime
from models.post_model import AnalysisStatus

class PostTag(BaseModel):
    tag: str
    class Config:
        from_attributes = True

class RedFlag(BaseModel):
    flag: str
    class Config:
        from_attributes = True

class TrustSignal(BaseModel):
    signal: str
    class Config:
        from_attributes = True

class ClaimSource(BaseModel):
    source_url: str
    class Config:
        from_attributes = True

class FactCheckSite(BaseModel):
    site_url: str
    class Config:
        from_attributes = True

class Claim(BaseModel):
    text: str
    credibility_score: Optional[int]
    confidence: Optional[str]
    reason: Optional[str]
    historical_context: Optional[str]
    sources: List[ClaimSource]
    fact_check_sites: List[FactCheckSite]
    class Config:
        from_attributes = True

class AnalysisStatusOut(BaseModel):
    post_id: int
    analysis_status: AnalysisStatus
    analysis_progress: float
    status_message: str
    
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class RefreshToken(BaseModel):
    refresh_token: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserOut(UserBase):
    id: int
    is_active: bool
    role: str

    class Config:
        from_attributes = True

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
    analysis_progress: float
    status_message: str
    short_title: Optional[str]
    summary_easy: Optional[str]
    credibility_score: Optional[int]
    bias: Optional[str]
    sentiment: Optional[str]
    risk_type: Optional[str]
    alt_headline_neutral: Optional[str]
    alt_headline_sensational: Optional[str]
    alt_headline_calm: Optional[str]
    
    analysis_raw: Optional[Dict[str, Any]]

    tags: List[PostTag]
    red_flags: List[RedFlag]
    claims: List[Claim]
    trust_signals: List[TrustSignal]

    latitude: Optional[float]
    longitude: Optional[float]

    is_upvoted: bool = False
    is_downvoted: bool = False

    upvote_downvote_count: int = 0
    view_count: int = 0

    class Config:
        from_attributes = True

class GameQuery(BaseModel):
    country: Optional[str]

class GameArticle(BaseModel):
    title: str
    body: str
    is_fake: bool
    source_url: str
