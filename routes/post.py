from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from database import get_db, SessionLocal
from models.user import User
from models.post_model import Post, AnalysisStatus
from models.recommendation_model import Recommendation
import schemas
from auth_deps import get_current_user, get_current_editor

import agent
import config
from recommendations import generate_recommendations 

def analyze_and_update_post(post_id: int, background_tasks: BackgroundTasks):
    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return

        post.analysis_status = AnalysisStatus.PROCESSING
        db.commit()

        article = agent.NewsArticle(title=post.title, body=post.body)
        engine = agent.NewsCredibilityEngine(tavily_key=config.TAVILY_API_KEY)
        analysis_results = engine.analyze(article)

        post.analysis = analysis_results
        post.analysis_status = AnalysisStatus.COMPLETED
        db.commit()
        print(f"Analysis complete for Post ID {post_id}.")

        
        background_tasks.add_task(generate_recommendations, post.id)

    except Exception as e:
        print(f"An error occurred during analysis for post {post_id}: {e}")
        if 'post' in locals():
            post.analysis_status = AnalysisStatus.FAILED
            db.commit()
    finally:
        db.close()


router = APIRouter(prefix="/posts", tags=["Posts"])

@router.get("/", response_model=List[schemas.PostOut])
def get_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(Post.created_at.desc()).limit(10).all()
    return posts

@router.post("/", response_model=schemas.PostOut, status_code=status.HTTP.HTTP_201_CREATED)
def create_post(
    post: schemas.PostCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_editor)
):
    db_post = Post(**post.dict(), created_by=current_user.id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)

    
    background_tasks.add_task(analyze_and_update_post, db_post.id, background_tasks)
    
    return db_post


@router.get("/{post_id}/recommendations", response_model=List[schemas.PostOut])
def get_recommendations(post_id: int, db: Session = Depends(get_db)):
   
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found"
        )

    recommendation_links = db.query(Recommendation).filter(Recommendation.source_post_id == post_id).all()
    
    recommended_ids = [rec.recommended_post_id for rec in recommendation_links]
    
    if not recommended_ids:
        return []

    recommended_posts = db.query(Post).filter(Post.id.in_(recommended_ids)).all()
    
    
    ordered_posts = sorted(recommended_posts, key=lambda p: recommended_ids.index(p.id))

    return ordered_posts


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post with id {post_id} not found"
        )
    if post.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post"
        )
    db.delete(post)
    db.commit()
    return
