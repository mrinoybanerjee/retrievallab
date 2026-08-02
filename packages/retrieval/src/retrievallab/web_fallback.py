from __future__ import annotations

from typing import Any

import httpx

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"


async def wikipedia_search(query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Search public Wikipedia metadata after local confidence falls below threshold.

    Only the rewritten query leaves the machine. Uploaded text and local passages are
    never included in this request.
    """

    parameters: dict[str, str | int] = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrlimit": limit,
        "prop": "extracts|info",
        "exintro": 1,
        "explaintext": 1,
        "inprop": "url",
        "format": "json",
        "origin": "*",
    }
    async with httpx.AsyncClient(timeout=4.0, follow_redirects=False) as client:
        response = await client.get(WIKIPEDIA_API, params=parameters)
        response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    return [
        {
            "title": page.get("title", "Untitled"),
            "url": page.get("fullurl"),
            "excerpt": page.get("extract", "")[:320],
            "provider": "Wikipedia",
        }
        for page in pages.values()
    ]
