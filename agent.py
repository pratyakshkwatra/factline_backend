from sqlalchemy.orm import Session
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, JSON, Enum, UniqueConstraint, Float, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db_base import Base
from google import genai
from google.genai import types
from tavily import TavilyClient
import json
import re
import enum
from typing import List, Dict, Any, Optional
from config import TAVILY_API_KEY
from models.post_model import (
    Post,
    AnalysisStatus,
    PostTag,
    RedFlag,
    TrustSignal,
    Claim,
    ClaimSource,
    FactCheckSite,
)
from schemas import UserOut, PostOut

class NewsArticle:
    def __init__(self, title: str, body: str, **extra):
        self.title = title.strip()
        self.body = body.strip()
        self.extra = extra

    def to_dict(self) -> Dict[str, Any]:
        d = {"title": self.title, "body": self.body}
        d.update(self.extra)
        return d

def web_search_func(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    if not query:
        return []
    tavily = TavilyClient(api_key=TAVILY_API_KEY)
    res = tavily.search(query=query, max_results=max_results)
    return res.get("results", [])

WEB_SEARCH_DECLARATION = types.FunctionDeclaration(
    name="web_search",
    description="Search the web to verify a claim or headline; returns concise, source-linked notes.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 10},
        },
        "required": ["query"],
    },
)

class NewsCredibilityEngine:
    def __init__(
        self,
        tavily_key: str,
        db: Session,
        post_id: int,
        cheap_model: str = "gemini-2.5-flash-lite",
        strong_model: str = "gemini-2.5-flash",
    ):
        self.tavily = TavilyClient(api_key=tavily_key)
        self.client = genai.Client()
        self.cheap_model_name = cheap_model
        self.strong_model_name = strong_model
        self.db = db
        self.post_id = post_id

    def _update_progress(self, progress: float, message: str, status: AnalysisStatus = None):
        post = self.db.query(Post).get(self.post_id)
        if not post:
            return
        post.analysis_progress = progress
        post.status_message = message
        if status:
            post.analysis_status = status
        self.db.commit()

    def analyze(self, article: NewsArticle) -> Dict[str, Any]:
        if not article.body.strip():
            self._update_progress(0, "Empty article body", AnalysisStatus.FAILED)
            return {"error": "Empty article body"}

        self._update_progress(5, "Init", AnalysisStatus.PROCESSING)
        lite = self._lite_transform(article)

        self._update_progress(40, "Lite analysis complete")
        deep = self._deep_analysis(article, lite)

        self._update_progress(95, "Merging data")
        out = {**lite, **deep}

        post = self.db.query(Post).get(self.post_id)
        if post:
            post.analysis_raw = out
            post.short_title = out.get("short_title")
            post.summary_easy = out.get("summary_easy")
            post.credibility_score = out.get("credibility_score")
            post.bias = out.get("bias")
            post.sentiment = out.get("sentiment")
            post.risk_type = out.get("risk_type")

            alt_headlines = out.get("alternative_headlines", {})
            post.alt_headline_neutral = alt_headlines.get("neutral")
            post.alt_headline_sensational = alt_headlines.get("sensational")
            post.alt_headline_calm = alt_headlines.get("calm")

            if "latitude" in out:
                post.latitude = out.get("latitude")
            if "longitude" in out:
                post.longitude = out.get("longitude")

            self._update_related_tables(post, out)

            post.analysis_status = AnalysisStatus.COMPLETED
            post.analysis_progress = 100
            post.status_message = "Analysis complete"
            self.db.commit()

        return out

    def _update_related_tables(self, post: Post, analysis_data: Dict[str, Any]):
        post.tags.clear()
        post.red_flags.clear()
        post.trust_signals.clear()
        post.claims.clear()

        for tag in analysis_data.get("tags", []):
            post.tags.append(PostTag(tag=tag.lower()))

        for flag in analysis_data.get("red_flags", []):
            post.red_flags.append(RedFlag(flag=flag))

        for signal in analysis_data.get("trust_signals", []):
            post.trust_signals.append(TrustSignal(signal=signal))

        for claim_data in analysis_data.get("claims", []):
            new_claim = Claim(
                text=claim_data.get("text"),
                credibility_score=claim_data.get("credibility_score"),
                confidence=claim_data.get("confidence"),
                reason=claim_data.get("reason"),
                historical_context=claim_data.get("historical_context")
            )

            for source_url in claim_data.get("sources", []):
                new_claim.sources.append(ClaimSource(source_url=source_url))

            for site_url in claim_data.get("fact_check_sites", []):
                new_claim.fact_check_sites.append(FactCheckSite(site_url=site_url))

            post.claims.append(new_claim)

        self.db.commit()

    def _lite_transform(self, article: NewsArticle) -> Dict[str, Any]:
        self._update_progress(10, "Lite transform started")
        sys = (
            "You simplify news for lay readers. Return strict JSON with keys: "
            "{'short_title': str, 'summary_easy': str, 'tags': [str]}."
            "Short title 5-8 words, neutral. Summary 4-6 simple sentences. Tags 2-5 topical words."
        )
        usr = json.dumps(article.to_dict(), ensure_ascii=False)

        response = self.client.models.generate_content(
            model=self.cheap_model_name,
            contents=types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=sys),
                    types.Part.from_text(text=usr)
                ]
            ),
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )

        self._update_progress(30, "Lite transform response received")
        return self._parse_json(
            response.text, {"short_title": "", "summary_easy": "", "tags": []}
        )

    def _deep_analysis(self, article: NewsArticle, lite: Dict[str, Any]) -> Dict[str, Any]:
        self._update_progress(45, "Deep analysis started")
        sys = (
            "You are a rigorous misinformation analyst. Extract atomic claims and assess them. "
            "You should call web_search to fact-check. Return STRICT JSON only with keys: "
            "{'credibility_score': int, 'bias': str, 'sentiment': str, 'risk_type': str, 'red_flags': [str], "
            "'claims': [{'text': str, 'credibility_score': int, 'confidence': 'Low'|'Medium'|'High', 'reason': str, 'sources': [str], 'fact_check_sites':[str], 'historical_context': str}], "
            "'trust_signals': [str], 'alternative_headlines': {'neutral': str, 'sensational': str, 'calm': str}, "
            "'latitude': float, 'longitude': float}."
        )
        usr = json.dumps({"article": article.to_dict(), "lite": lite}, ensure_ascii=False)

        tools = types.Tool(function_declarations=[WEB_SEARCH_DECLARATION])
        config = types.GenerateContentConfig(tools=[tools])

        contents_list = [
            types.Content(role="user", parts=[
                types.Part.from_text(text=sys),
                types.Part.from_text(text=usr)
            ])
        ]

        response = self.client.models.generate_content(
            model=self.strong_model_name,
            contents=contents_list,
            config=config,
        )

        self._update_progress(55, "Deep analysis first pass")

        while response.candidates and any(p.function_call for p in response.candidates[0].content.parts):
            tool_calls = [p.function_call for p in response.candidates[0].content.parts if p.function_call]
            for call in tool_calls:
                function_name = call.name
                arguments = call.args

                if function_name == "web_search":
                    q = arguments.get("query", "").strip()
                    k = int(arguments.get("max_results", 5))
                    self._update_progress(60, f"Searching: {q}")
                    s = web_search_func(query=q, max_results=k)

                    contents_list.append(types.Content(
                        role="model",
                        parts=[types.Part.from_function_call(name=function_name, args=arguments)]
                    ))
                    contents_list.append(types.Content(
                        role="tool",
                        parts=[types.Part.from_function_response(name=function_name, response={"results": s})]
                    ))

            response = self.client.models.generate_content(
                model=self.strong_model_name,
                contents=contents_list,
                config=config,
            )
            self._update_progress(70, "Deep analysis post-tools")

        self._update_progress(85, "Parsing deep analysis result")
        return self._parse_json(
            response.text,
            {
                "credibility_score": 0,
                "bias": "",
                "sentiment": "",
                "risk_type": "",
                "red_flags": [],
                "claims": [],
                "trust_signals": [],
                "alternative_headlines": {"neutral": "", "sensational": "", "calm": ""},
                "latitude": None,
                "longitude": None,
            },
        )


    def _parse_json(self, text: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        if not text:
            return fallback
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(
                r"^```(?:json)?\s*|\s*```$", "", cleaned,
                flags=re.IGNORECASE | re.DOTALL
            ).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
                if m:
                    return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return fallback