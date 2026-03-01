"""Tests for ToolService web/deep search parsing."""

from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from sidecar.services.tool_service import ToolService


@pytest.mark.asyncio
async def test_web_search_success_parses_results():
    service = ToolService()

    payload = {
        "Heading": "Python",
        "AbstractText": "Python is a programming language.",
        "AbstractURL": "https://example.com/python",
        "RelatedTopics": [
            {
                "Text": "Python (programming language) - High-level language",
                "FirstURL": "https://example.com/python-lang",
            }
        ],
    }

    mock_response = MagicMock()
    mock_response.json.return_value = payload
    mock_response.raise_for_status.return_value = None

    with patch("sidecar.services.tool_service.httpx.AsyncClient") as client_cls:
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.get.return_value = mock_response
        client_cls.return_value = client

        res = await service.web_search("python", limit=2)

    assert res["status"] == "success"
    assert len(res["results"]) >= 1
    assert res["results"][0]["title"]


@pytest.mark.asyncio
async def test_deep_search_marks_mode():
    service = ToolService()

    with patch.object(service, "web_search", new=AsyncMock(return_value={
        "status": "success",
        "query": "q",
        "results": [{"title": "a", "url": "u", "snippet": "s"}] * 20,
    })):
        res = await service.deep_search("q", limit=5)

    assert res["status"] == "success"
    assert res["mode"] == "deep"
    assert len(res["results"]) == 10


def test_build_search_context_empty():
    service = ToolService()
    assert service.build_search_context({"results": []}, "Web") == ""
