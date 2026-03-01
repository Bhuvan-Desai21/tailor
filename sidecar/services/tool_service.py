"""Utilities for lightweight tool augmentation in chat flows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from urllib.parse import quote_plus
from typing import Any, Dict, List

from loguru import logger

try:
    import httpx
except ImportError:  # pragma: no cover - dependency controlled by runtime env
    httpx = None


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class ToolService:
    """Small utility service for web/deep search and prompt context helpers."""

    DDG_API_URL = "https://duckduckgo.com/?q={query}&format=json&no_redirect=1&no_html=1"

    def __init__(self) -> None:
        self._logger = logger.bind(component="ToolService")

    async def web_search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Run lightweight web search via DuckDuckGo instant answer API."""
        if not query:
            return {"status": "error", "error": "query is required", "results": []}

        if httpx is None:
            return {
                "status": "error",
                "error": "httpx is not available",
                "results": [],
            }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                url = self.DDG_API_URL.format(query=quote_plus(query))
                res = await client.get(url)
                res.raise_for_status()

            payload = res.json()
            results = self._parse_ddg_results(payload)[:limit]
            return {
                "status": "success",
                "query": query,
                "results": [r.__dict__ for r in results],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            self._logger.warning(f"web_search failed: {exc}")
            return {"status": "error", "error": str(exc), "results": []}

    async def deep_search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Deep search currently performs broader result extraction with larger limits."""
        base = await self.web_search(query=query, limit=max(10, limit))
        if base.get("status") != "success":
            return base

        base["mode"] = "deep"
        base["results"] = base.get("results", [])[: limit * 2]
        return base

    def build_search_context(self, search_payload: Dict[str, Any], heading: str) -> str:
        results = search_payload.get("results", [])
        if not results:
            return ""

        lines = [heading]
        for idx, item in enumerate(results, start=1):
            title = item.get("title") or "Untitled"
            snippet = item.get("snippet") or ""
            url = item.get("url") or ""
            lines.append(f"{idx}. {title}\n   {snippet}\n   Source: {url}")
        return "\n".join(lines)

    def _parse_ddg_results(self, payload: Dict[str, Any]) -> List[SearchResult]:
        results: List[SearchResult] = []

        abstract = payload.get("AbstractText")
        abstract_url = payload.get("AbstractURL")
        heading = payload.get("Heading")
        if abstract:
            results.append(
                SearchResult(
                    title=heading or "DuckDuckGo Instant Answer",
                    url=abstract_url or "https://duckduckgo.com",
                    snippet=abstract.strip(),
                )
            )

        for item in payload.get("RelatedTopics", []):
            if "Topics" in item:
                for nested in item.get("Topics", []):
                    parsed = self._topic_to_result(nested)
                    if parsed:
                        results.append(parsed)
            else:
                parsed = self._topic_to_result(item)
                if parsed:
                    results.append(parsed)

        deduped: List[SearchResult] = []
        seen = set()
        for item in results:
            key = (item.title, item.url)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        return deduped

    def _topic_to_result(self, item: Dict[str, Any]) -> SearchResult | None:
        text = unescape(item.get("Text", "")).strip()
        url = item.get("FirstURL", "")
        if not text and not url:
            return None

        title, snippet = self._split_title_snippet(text)
        return SearchResult(title=title, url=url, snippet=snippet)

    def _split_title_snippet(self, text: str) -> tuple[str, str]:
        cleaned = re.sub(r"\s+", " ", text).strip()
        if " - " in cleaned:
            title, snippet = cleaned.split(" - ", 1)
            return title.strip(), snippet.strip()
        return cleaned[:80], cleaned
