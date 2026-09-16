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
            