from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.user import User
from models.post_model import Post, AnalysisStatus, Upvote, Downvote, View
import schemas
from auth_deps import get_current_user, get_current_editor
import config
from datetime import datetime, timedelta
from sqlalchemy import func, desc, asc

router = APIRouter(prefix="/posts", tags=["Posts"])

@router.post("/", response_model=schemas.PostOut)
def create_post(
    post: schemas.PostCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_editor)
):
    db_post = Post(
        **post.dict(),
        created_by=current_user.id,
        analysis_status=AnalysisStatus.PROCESSING,
        analysis_progress=0.0,
        status_message="Analysis pending"
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)

    background_tasks.add_task(analyze_and_update_post, db_post.id)

    return db_post

def analyze_and_update_post(post_id: int):
    try:
        db_session = next(get_db())
        
        engine = agent.NewsCredibilityEngine(
            tavily_key=config.TAVILY_API_KEY,
            db=db_session,
            post_id=post_id
        )
        
        post = db_session.query(Post).filter(Post.id == post_id).first()
        if post:
            news_article = agent.NewsArticle(title=post.title, body=post.body)
            engine.analyze(news_article)
        
    except Exception as e:
        db_session = next(get_db())
        post = db_session.query(Post).filter(Post.id == post_id).first()
        if post:
            post.analysis_status = AnalysisStatus.FAILED
            post.status_message = f"Analysis failed: {str(e)}"
            db_session.commit()
    finally:
        db_session.close()

@router.get("/{post_id}/status", response_model=schemas.AnalysisStatusOut)
def get_analysis_status(
    post_id: int,
    db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return {
        "post_id": post.id,
        "analysis_status": post.analysis_status,
        "analysis_progress": post.analysis_progress,
        "status_message": post.status_message
    }

@router.post("/{post_id}/upvote", status_code=201)
def add_upvote(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing_upvote = db.query(Upvote).filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing_upvote:
        db.delete(existing_upvote)
        db.commit()
        return {"message": "Upvote Neutralised"}

    existing_downvote = db.query(Downvote).filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing_downvote:
        db.delete(existing_downvote)
        db.commit()

    db_upvote = Upvote(user_id=current_user.id, post_id=post_id)
    db.add(db_upvote)
    db.commit()
    return {"message": "Upvoted"}

@router.post("/{post_id}/downvote", status_code=201)
def add_downvote(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing_downvote = db.query(Downvote).filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing_downvote:
        db.delete(existing_downvote)
        db.commit()
        return {"message": "Neutralised Downvote"}

    existing_upvote = db.query(Upvote).filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing_upvote:
        db.delete(existing_upvote)
        db.commit()

    db_downvote = Downvote(user_id=current_user.id, post_id=post_id)
    db.add(db_downvote)
    db.commit()
    return {"message": "Downvoted"}

@router.post("/{post_id}/view", status_code=201)
def add_view(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    db_view = View(user_id=current_user.id, post_id=post_id)
    db.add(db_view)
    db.commit()
    return {"message": "View recorded"}



@router.get("/breaking-news", response_model=List[schemas.PostOut])
def get_breaking_news(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    posts_query = (
        db.query(Post)
        .filter(Post.analysis_status == AnalysisStatus.COMPLETED)
        .all()
    )

    if not posts_query:
        return []

    upvote_counts = dict(
        db.query(Upvote.post_id, func.count(Upvote.id))
        .group_by(Upvote.post_id)
        .all()
    )
    downvote_counts = dict(
        db.query(Downvote.post_id, func.count(Downvote.id))
        .group_by(Downvote.post_id)
        .all()
    )
    view_counts = dict(
        db.query(View.post_id, func.count(View.id))
        .group_by(View.post_id)
        .all()
    )

    ranked_posts = []
    now = datetime.utcnow()

    for post in posts_query:
        uv = upvote_counts.get(post.id, 0)
        dv = downvote_counts.get(post.id, 0)
        vc = view_counts.get(post.id, 0)

        hours_old = (now - post.created_at.replace(tzinfo=None)).total_seconds() / 3600

        recency_weight = 1 / (1 + hours_old/12)

        score = (uv * 3 + vc * 1 - dv * 2) * recency_weight

        ranked_posts.append((score, uv, vc, -dv, post))

    ranked_posts.sort(key=lambda x: (x[0], x[1], x[2], x[3]), reverse=True)

    top_posts = [schemas.PostOut.from_orm(p[4]).copy(update={
        "upvote_downvote_count": p[1] - (-p[3]),
        "view_count": p[2],
        "is_upvoted": db.query(Upvote).filter_by(user_id=current_user.id, post_id=p[4].id).first() is not None,
        "is_downvoted": db.query(Downvote).filter_by(user_id=current_user.id, post_id=p[4].id).first() is not None,
    }) for p in ranked_posts[:5]]

    return top_posts

@router.get("/recommendations", response_model=List[schemas.PostOut])
def get_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    last_upvotes = (
        db.query(Upvote)
        .filter_by(user_id=current_user.id)
        .order_by(Upvote.created_at.desc())
        .limit(20)
        .all()
    )
    last_downvotes = (
        db.query(Downvote)
        .filter_by(user_id=current_user.id)
        .order_by(Downvote.created_at.desc())
        .limit(20)
        .all()
    )
    last_views = (
        db.query(View)
        .filter_by(user_id=current_user.id)
        .order_by(View.created_at.desc())
        .limit(20)
        .all()
    )

    scores = {}
    for u in last_upvotes:
        scores[u.post_id] = scores.get(u.post_id, 0) + 2
    for v in last_views:
        scores[v.post_id] = scores.get(v.post_id, 0) + 1
    for d in last_downvotes:
        scores[d.post_id] = scores.get(d.post_id, 0) - 2

    if not scores:
        posts = (
            db.query(Post)
            .filter(Post.analysis_status == AnalysisStatus.COMPLETED)
            .order_by(Post.created_at.desc())
            .limit(10)
            .all()
        )
    else:
        top_post_ids = sorted(scores.keys(), key=lambda pid: scores[pid], reverse=True)[:5]
        top_posts = (
            db.query(Post)
            .filter(Post.id.in_(top_post_ids), Post.analysis_status == AnalysisStatus.COMPLETED)
            .all()
        )
        
        similar_ids = find_similar_posts(db=db, source_posts=top_posts)

        posts = top_posts[:]

        if similar_ids:
            similar_posts = (
                db.query(Post)
                .filter(Post.id.in_(similar_ids), Post.analysis_status == AnalysisStatus.COMPLETED)
                .all()
            )
            posts.extend(similar_posts)

        seen = set()
        unique_posts = []
        for p in posts:
            if p.id not in seen:
                seen.add(p.id)
                unique_posts.append(p)
        posts = unique_posts[:10]

    post_ids = [p.id for p in posts]

    upvoted_ids = {
        u.post_id for u in db.query(Upvote)
        .filter(Upvote.user_id == current_user.id, Upvote.post_id.in_(post_ids)).all()
    }
    downvoted_ids = {
        d.post_id for d in db.query(Downvote)
        .filter(Downvote.user_id == current_user.id, Downvote.post_id.in_(post_ids)).all()
    }

    upvote_counts = dict(
        db.query(Upvote.post_id, func.count(Upvote.id))
        .filter(Upvote.post_id.in_(post_ids))
        .group_by(Upvote.post_id)
        .all()
    )
    downvote_counts = dict(
        db.query(Downvote.post_id, func.count(Downvote.id))
        .filter(Downvote.post_id.in_(post_ids))
        .group_by(Downvote.post_id)
        .all()
    )
    view_counts = dict(
        db.query(View.post_id, func.count(View.id))
        .filter(View.post_id.in_(post_ids))
        .group_by(View.post_id)
        .all()
    )

    result = []
    for post in posts:
        uv = upvote_counts.get(post.id, 0)
        dv = downvote_counts.get(post.id, 0)
        vc = view_counts.get(post.id, 0)
        result.append(
            schemas.PostOut.from_orm(post).copy(update={
                "is_upvoted": post.id in upvoted_ids,
                "is_downvoted": post.id in downvoted_ids,
                "upvote_downvote_count": uv - dv,
                "view_count": vc,
            })
        )

    return result

def find_similar_posts(db: Session, source_posts: List[Post]) -> List[int]:
    if not source_posts:
        return []

    source_tags = set()
    source_keywords = set()

    for post in source_posts:
        if getattr(post, "tags", None):
            if isinstance(post.tags, list):
                source_tags.update([str(t).strip().lower() for t in post.tags])
            else:
                source_tags.update([str(t).strip().lower() for t in str(post.tags).split(",") if t.strip()])

        if post.title:
            for word in post.title.lower().split():
                if len(word) > 2:
                    source_keywords.add(word)

    query = db.query(Post).filter(Post.analysis_status == AnalysisStatus.COMPLETED)

    similar_posts = []
    source_ids = {p.id for p in source_posts}

    for candidate in query.all():
        if candidate.id in source_ids:
            continue

        score = 0

        if getattr(candidate, "tags", None):
            candidate_tags = (
                candidate.tags if isinstance(candidate.tags, list)
                else [t.strip().lower() for t in str(candidate.tags).split(",") if t.strip()]
            )
            overlap = source_tags.intersection(set(candidate_tags))
            score += len(overlap) * 2

        if candidate.title:
            candidate_words = set(candidate.title.lower().split())
            overlap = source_keywords.intersection(candidate_words)
            score += len(overlap)

        if score > 0:
            similar_posts.append((candidate.id, score))

    if not similar_posts:
        posts = (
            db.query(Post)
            .filter(~Post.id.in_(source_ids), Post.analysis_status == AnalysisStatus.COMPLETED)
            .order_by(Post.created_at.desc())
            .limit(10)
            .all()
        )
        return [p.id for p in posts]

    similar_posts.sort(key=lambda x: x[1], reverse=True)
    return [pid for pid, _ in similar_posts[:10]]