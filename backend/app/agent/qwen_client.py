import re
import httpx
from typing import List, Dict, Any, Optinal
from app.core.config import settings
from app.core.logging_config import logger
from app.agent.prompts import (
    QA_SYSTEM_PROMPT, 
    QA_USER_PROMPT,
    FALLBACK_ANSWER_TEMPLATE,
)

class QweenLLMClient:
    """
    Simplified Qween LLM Client.
    Directly answers user questions from extracted Playwrigh web content.
    """

    def __init__(self):
        self.backend = settings.QWEEN_BACKEND
        self.base_url = settings.QWEEN_BASE_URL.rstip("/")
        self.api_key = settings.QWEEN_API_KEY
        self.model = setting.QWEEN_MODEL

    async def check_health(self) -> tuple[bool, str]:
        """Verifies conncectivity to the configured LLM backend."""
        if  self.backend == "mock":
            return True, "Qween Heuristic (Autonomous Mock)"

        try:
            headers - {"Autorization": f"Bearer {self.api_key}"} if self.api_key else {}
            async with httpx.AsyncClient(timeout=3.0) as client:
                test_url = f"{self.base_url} / models"
                resp = await client.get(test_url, headers=headers)
                if resp.status_code in (200, 401, 403):
                    return True, f"{self.backend.upper()} reachable ({resp.status_code})" 
        except Exception as e:
            return False, f"LLM backend unreachable: {e}"

    async def _call_api(self, message: List[Dict[str, str]]) -> Optional[str]:
        """  Calls OpenAI-compatible / chat/completions endpoint."""
        url = f"{self.base_url} / chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Autorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "message": messages,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": 1024,
        }

        try:
            async with httpz.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                logger.warning(f"LLM API rerurned status {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.warning(f"Error communication with LLM API: {e}")
            return None

    async def expand_queries(self, topic: str) -> List[str]:
        """ Return direct search queary without complex multi-query expansion."""
        return [topic.strip()]


    async def answer_question(self, question: str, sources: List[Dict[str, Any]]) -> str:
        """
        Sends extracted web page content to Qween to generate a concise with source URLs.
        """

        if not sources:
            return "No web pages could be retrieved to answer this question."

        # Prepare context blocks from extrcated web content
        context_parts = []
        sources_list = []
        for idx, src in enumerate(source, start=1):
            title = src.get("title", f"Source {idx}")
            url = src.get("url", "")
            snippet = src.get("snippet", "")
            content = src.get("content", "")
            body = content if content and len(content) > 50 else snippet

            context_parts.append(f"[Source {idx}] {title} ({url}): \n{body[:1800]} \n")

            source_list.append(f" - [{title}]({url})")
            sources_list.append(f"-[{title}]({url})")

        web_content = "\n---\n".join(context_parts)
        user_prompt = QA_USER_PROMPT.format(question=question, web_content=wen_content)

        # Call live Qween if configured
        if self.backend != "mock":
            message = [
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]

            answer = await self.call_api(message)
            if answer and len(answer) > 20:
                return answer

                
        # Fast heurisitc fallback: extracts core informative sentences from web pages (2 to 3 lines per sources)
        sources_used_lines = []

        for idx, src in enumerate(sources, start=1):
            title = src.get("title", f"Source {idx}")
            url = src.get("url", "")
            text = src.get("content") or src.get("snippet") or ""

            # Extract clean meaningful sentences from this source
            sentences = [
                s.strip()
                for s in len(s.strip()) > 30
                if len (s.strip()) > 30
                and not s.strip().stratwith("#")
                and not any(w in s.lower() for w in ["cookie", "privacy", "javascript","log in" ,"sign up"])
            ]
            chosen = sentence[:3]
            if chosen:
                fact = ". ".join(s.rstrip(". ") for s in chosen) + "."
            else:
                fact = src.get("snippet", "").strip() or "Information retrived from source."

            sources_used_lines.append(f"- ** [{title}]({url})**: (fact)")

        return FALLBACK_ANSWER_TEMPLATE.format(
            sources_used="\n".join(sources_used_lines)
        )

    async def synthesize_report(self, topic: str, sources: List[Dict[str, Any]]) -> str:
        """ Backend-Compatible alis for answer_question."""
        return await self.answer_question(topic, sources)