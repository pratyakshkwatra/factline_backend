import random
from fastapi import APIRouter, Depends, HTTPException, status
import schemas
import game_logic

router = APIRouter(prefix="/game", tags=["Game"])

@router.post("/generate", response_model=schemas.GameArticle)
def generate_game_article(
    query: schemas.GameQuery,
):
    real_article = game_logic.fetch_real_article(
        country=query.country,
    )

    if not real_article:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not fetch a news article at this time. Please try another topic."
        )

    if random.random() < 0.5:
        doctored_article = game_logic.doctor_article_with_gemini(real_article)
        if not doctored_article:
            return schemas.GameArticle(
                title=real_article['title'],
                body=real_article['body'],
                is_fake=False,
                source_url=real_article['source_url']
            )
        return doctored_article
    else:
        return schemas.GameArticle(
            title=real_article['title'],
            body=real_article['body'],
            is_fake=False,
            source_url=real_article['source_url']
        )