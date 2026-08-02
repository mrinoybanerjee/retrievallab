from __future__ import annotations

import json
from pathlib import Path

from retrievallab.models import Chunk
from retrievallab.text import token_windows


def load_demo_corpus(path: Path) -> list[Chunk]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    chunks: list[Chunk] = []
    for page in raw["pages"]:
        for child, (excerpt, start, end) in enumerate(token_windows(page["text"], 500, 50)):
            chunks.append(
                Chunk(
                    id=f"demo-p{page['page']}-c{child}",
                    parent_id=f"demo-p{page['page']}",
                    source=raw["title"],
                    page=page["page"],
                    section=page["section"],
                    text=excerpt,
                    token_start=start,
                    token_end=end,
                    metadata={"topic": page["topic"], "year": "2026"},
                    coordinates=(54.0, 96.0, 558.0, 720.0),
                )
            )
    return chunks
