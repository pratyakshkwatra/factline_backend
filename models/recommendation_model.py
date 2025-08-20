from sqlalchemy import Column, Integer, ForeignKey
from db_base import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    source_post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    recommended_post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
