from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, JSON, Enum, UniqueConstraint, Float, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db_base import Base
import enum

class AnalysisStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    
    analysis_status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False)
    analysis_progress = Column(Float, default=0.0, nullable=False)  
    status_message = Column(String, default="Not started", nullable=False)  

    
    short_title = Column(String, index=True, nullable=True)
    summary_easy = Column(Text, nullable=True)
    credibility_score = Column(Integer, index=True, nullable=True)
    bias = Column(String, nullable=True)
    sentiment = Column(String, nullable=True)
    risk_type = Column(String, nullable=True)

    
    alt_headline_neutral = Column(String, nullable=True)
    alt_headline_sensational = Column(String, nullable=True)
    alt_headline_calm = Column(String, nullable=True)
    
    analysis_raw = Column(JSON, nullable=True)

    owner = relationship("User", back_populates="posts")

    upvotes = relationship("Upvote", back_populates="post", cascade="all, delete-orphan")
    downvotes = relationship("Downvote", back_populates="post", cascade="all, delete-orphan")
    views = relationship("View", back_populates="post", cascade="all, delete-orphan")

    tags = relationship("PostTag", back_populates="post", cascade="all, delete-orphan")
    red_flags = relationship("RedFlag", back_populates="post", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="post", cascade="all, delete-orphan")
    trust_signals = relationship("TrustSignal", back_populates="post", cascade="all, delete-orphan")

class PostTag(Base):
    __tablename__ = "post_tags"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String, index=True, nullable=False)

    post = relationship("Post", back_populates="tags")

class RedFlag(Base):
    __tablename__ = "red_flags"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    flag = Column(String, nullable=False)

    post = relationship("Post", back_populates="red_flags")

class TrustSignal(Base):
    __tablename__ = "trust_signals"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    signal = Column(String, nullable=False)

    post = relationship("Post", back_populates="trust_signals")

class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)

    text = Column(Text, nullable=False)
    credibility_score = Column(Integer, nullable=True)
    confidence = Column(String, nullable=True)  
    reason = Column(Text, nullable=True)
    historical_context = Column(Text, nullable=True)

    post = relationship("Post", back_populates="claims")

    sources = relationship("ClaimSource", back_populates="claim", cascade="all, delete-orphan")
    fact_check_sites = relationship("FactCheckSite", back_populates="claim", cascade="all, delete-orphan")

class ClaimSource(Base):
    __tablename__ = "claim_sources"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    source_url = Column(String, nullable=False)

    claim = relationship("Claim", back_populates="sources")

class FactCheckSite(Base):
    __tablename__ = "fact_check_sites"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    site_url = Column(String, nullable=False)

    claim = relationship("Claim", back_populates="fact_check_sites")

class Upvote(Base):
    __tablename__ = "upvotes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("Post", back_populates="upvotes")
    user = relationship("User", back_populates="upvotes")

    __table_args__ = (UniqueConstraint("user_id", "post_id", name="unique_upvote"),)

class Downvote(Base):
    __tablename__ = "downvotes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("Post", back_populates="downvotes")
    user = relationship("User", back_populates="downvotes")

    __table_args__ = (UniqueConstraint("user_id", "post_id", name="unique_downvote"),)

class View(Base):
    __tablename__ = "views"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    post = relationship("Post", back_populates="views")
    user = relationship("User", back_populates="views")