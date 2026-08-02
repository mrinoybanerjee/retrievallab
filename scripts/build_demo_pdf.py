from __future__ import annotations

import json
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "demo"


def main() -> None:
    corpus = json.loads((DATA / "corpus.json").read_text(encoding="utf-8"))
    document = fitz.open()
    for item in corpus["pages"]:
        page = document.new_page(width=612, height=792)
        page.insert_text((48, 46), "RETRIEVALLAB / FIELD GUIDE", fontsize=8, fontname="cour", color=(0.35, 0.37, 0.31))
        page.insert_text((548, 46), f"{item['page']:02d}", fontsize=8, fontname="cour", color=(0.35, 0.37, 0.31))
        page.insert_textbox(
            fitz.Rect(48, 92, 545, 160),
            item["section"],
            fontsize=23,
            fontname="hebo",
            color=(0.08, 0.09, 0.07),
            lineheight=1.08,
        )
        page.insert_textbox(
            fitz.Rect(48, 182, 548, 640),
            item["text"],
            fontsize=12,
            fontname="heit",
            color=(0.16, 0.17, 0.14),
            lineheight=1.55,
        )
        page.draw_line((48, 706), (548, 706), color=(0.72, 0.73, 0.68), width=0.5)
        page.insert_text(
            (48, 728), f"TOPIC / {item['topic'].upper()}", fontsize=8, fontname="cour", color=(0.35, 0.37, 0.31)
        )
    output = DATA / "retrieval-handbook.pdf"
    document.set_metadata(
        {"title": corpus["title"], "author": "RetrievalLab", "subject": "Observable retrieval systems"}
    )
    document.save(output, garbage=4, deflate=True)
    document.close()
    print(f"Generated {output.relative_to(ROOT)} ({len(corpus['pages'])} pages)")


if __name__ == "__main__":
    main()
