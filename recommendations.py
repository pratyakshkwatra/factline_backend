from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from models.post_model import Post, AnalysisStatus
from models.recommendation_model import Recommendation
from database import SessionLocal

def generate_recommendations(post_id: int):
    
    db = SessionLocal()
    try:
        
        completed_posts = db.query(Post).filter(
            Post.analysis_status == AnalysisStatus.COMPLETED,
            Post.analysis.isnot(None)
        ).all()

        if len(completed_posts) < 2:
            print("Not enough posts with completed analysis to generate recommendations.")
            return

        
        post_ids = [p.id for p in completed_posts]
        
        corpus = [" ".join(p.analysis.get("tags", [])) for p in completed_posts]

        
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(corpus)

        
        cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

        
        try:
            idx = post_ids.index(post_id)
        except ValueError:
            print(f"Post ID {post_id} not found in posts with completed analysis.")
            return

        
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

        
        
        top_indices = [i[0] for i in sim_scores[1:6]]
        recommended_post_ids = [post_ids[i] for i in top_indices]

        
        db.query(Recommendation).filter(Recommendation.source_post_id == post_id).delete()

        for rec_id in recommended_post_ids:
            recommendation = Recommendation(
                source_post_id=post_id,
                recommended_post_id=rec_id
            )
            db.add(recommendation)
        
        db.commit()
        print(f"Successfully generated and stored recommendations for Post ID {post_id}.")

    except Exception as e:
        print(f"Error generating recommendations for post {post_id}: {e}")
        db.rollback()
    finally:
        db.close()
