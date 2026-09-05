"""Base class for all specialized agents.

Contract: every agent exposes a single async ``run()`` method that returns an
:class:`AgentResult`. Agents never call Claude — the Chief Analyst calls agents
as tools and then calls Claude to synthesize.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from ..models import AgentResult


class BaseAgent(ABC):
    """Abstract base for all specialized agents."""

    def __init__(self, supabase_url: str = "", service_role_key: str = "") -> None:
        self._supabase_url = supabase_url
        self._service_role_key = service_role_key

    @abstractmethod
    async def run(self, **kwargs: Any) -> AgentResult:
        """Execute the agent and return structured evidence."""

    async def _supabase_get(self, path: str, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
        if not self._supabase_url:
            return []
        url = f"{self._supabase_url}/rest/v1/{path}"
        headers = {
            "apikey": self._service_role_key,
            "Authorization": f"Bearer {self._service_role_key}",
        }
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(url, headers=headers, params=params or {}, timeout=10.0)
            return res.json() if res.status_code == 200 else []
        except Exception as exc:
            return []
