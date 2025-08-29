from newsapi import NewsApiClient
import google.genai as genai
from google.genai import types
from config import NEWS_API_KEY, GOOGLE_API_KEY
import random

newsapi = NewsApiClient(api_key=NEWS_API_KEY)

def fetch_real_article(country: str) -> dict:
    try:
        response = newsapi.get_top_headlines(
            country=country.lower(),
            page_size=10
        )

        articles = response.get("articles", [])
        if not articles:
            print("NewsAPI returned no articles.")
            return None
        
        articles_final = []

        for article in articles:
            body = article.get("description") or article.get("content")
            
            if article.get("title") and body and article.get("url"):
                articles_final.append({
                    "title": article.get("title"),
                    "body": body,
                    "source_url": article.get("url"),
                })

        if len(articles_final) != 0:
            article_sel = random.choice(articles_final)
            return {
                "title": article.get("title"),
                "body": body,
                "source_url": article.get("url"),
            }
        
        print("No articles with sufficient content found.")
        return None

    except Exception as e:
        print(f"Error fetching from NewsAPI: {e}")
        return None
    
def doctor_article_with_gemini(article: dict) -> dict:
    if not article or not article.get('body'):
        return None

    client = genai.Client(api_key=GOOGLE_API_KEY)

    prompt = f"""
    You are a misinformation generator for a game. Your task is to rewrite the following news summary to include subtle, believable falsehoods or a slightly altered narrative. The goal is to make it difficult, but not impossible, for a user to tell that it's fake.

    RULES:
    1.  Do not state that you are an AI or that the content is fabricated.
    2.  Maintain the original tone and style of the summary.
    3.  The changes should be subtle (e.g., alter a key statistic, change a quote slightly, invent a plausible but fake source).
    4.  Return ONLY the doctored summary as a single block of text. Do not include the title or any other text.

    ORIGINAL ARTICLE TITLE: "{article['title']}"
    ORIGINAL ARTICLE SUMMARY:
    ---
    {article['body']}
    ---
    """

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)]
            )
        )
        doctored_body = response.text.strip()
        
        return {
            "title": article['title'],
            "body": doctored_body,
            "is_fake": True,
            "source_url": article['source_url']
        }
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None