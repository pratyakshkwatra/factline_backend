from sqlalchemy import Column, Integer, String, Boolean, Enum
from sqlalchemy.orm import relationship
from db_base import Base
import enum

class UserRole(enum.Enum):
    user = "user"
    editor = "editor"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)

    posts = relationship("Post", back_populates="owner")
    upvotes = relationship("Upvote", back_populates="user", cascade="all, delete-orphan")
    downvotes = relationship("Downvote", back_populates="user", cascade="all, delete-orphan")
    views = relationship("View", back_populates="user", cascade="all, delete-orphan")

