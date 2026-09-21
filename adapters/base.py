from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from playwright.async_api import Page
from core.llm_engine import LLMEngine
from adapters.browser_manager import BrowserManager


class BaseJobPlatform(ABC):
    def __init__(self, browser_manager: BrowserManager, llm_engine: LLMEngine):
        self.browser_manager = browser_manager
        self.llm = llm_engine
        self.platform_name = "base"

    @abstractmethod
    async def is_authenticated(self, page: Page) -> bool:
        """Verifica si la sesión del usuario está activa en la plataforma."""
        pass

    @abstractmethod
    async def search_jobs(self, query: str, remote_only: bool = True, max_results: int = 15) -> List[Dict[str, Any]]:
        """Busca vacantes que coincidan con la búsqueda y extrae metadata."""
        pass

    @abstractmethod
    async def apply(self, job_data: Dict[str, Any], auto_submit: bool = False) -> Dict[str, Any]:
        """Aplica a la vacante respondiendo cuestionarios mediante el LLM."""
        pass
