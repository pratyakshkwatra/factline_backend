import json
import re
from typing import List, Dict, Any
from google import genai
from google.genai import types
from tavily import TavilyClient
from config import TAVILY_API_KEY

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
        cheap_model: str = "gemini-2.5-flash-lite",
        strong_model: str = "gemini-2.5-flash",
    ):
        self.tavily = TavilyClient(api_key=tavily_key)
        self.client = genai.Client()
        self.cheap_model_name = cheap_model
        self.strong_model_name = strong_model

    def analyze(self, article: NewsArticle) -> Dict[str, Any]:
        if not article.body.strip():
            return {"error": "Empty article body"}

        print("5% | Init")
        lite = self._lite_transform(article)
        print("40% | LiteDone")
        deep = self._deep_analysis(article, lite)
        print("95% | MergeData")
        out = {**lite, **deep}
        print("100% | Done")
        return out

    def _lite_transform(self, article: NewsArticle) -> Dict[str, Any]:
        print("10% | LiteStart")
        sys = (
            "You simplify news for lay readers. Return strict JSON with keys: "
            "{'short_title': str, 'summary_easy': str, 'tags': [str]}."
            "Short title 5-8 words, neutral. Summary 2-3 simple sentences. Tags 2-5 topical words."
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
        
        print("30% | LiteResp")
        return self._parse_json(
            response.text, {"short_title": "", "summary_easy": "", "tags": []}
        )

    def _deep_analysis(self, article: NewsArticle, lite: Dict[str, Any]) -> Dict[str, Any]:
        print("45% | DeepStart")
        sys = (
            "You are a rigorous misinformation analyst. Extract atomic claims and assess them. "
            "You should call web_search to fact-check. Return STRICT JSON only with keys: "
            "{'credibility_score': int, 'bias': str, 'sentiment': str, 'risk_type': str, 'red_flags': [str], "
            "'claims': [{'text': str, 'credibility_score': int, 'confidence': 'Low'|'Medium'|'High', 'reason': str, 'sources': [str], 'fact_check_sites':[str], 'historical_context': str}], "
            "'trust_signals': [str], 'alternative_headlines': {'neutral': str, 'sensational': str}}."
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
        
        print("55% | FirstPass")

        while response.candidates and any(p.function_call for p in response.candidates[0].content.parts):
            tool_calls = [p.function_call for p in response.candidates[0].content.parts if p.function_call]
            for call in tool_calls:
                function_name = call.name
                arguments = call.args
                
                if function_name == "web_search":
                    q = arguments.get("query", "").strip()
                    k = int(arguments.get("max_results", 5))
                    print(f"60% | Searching: {q}")
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
            print("70% | PostTools")
        
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
                "alternative_headlines": {"neutral": "", "sensational": ""},
            },
        )

    def _parse_json(self, text: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        print("85% | Parsing")
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












