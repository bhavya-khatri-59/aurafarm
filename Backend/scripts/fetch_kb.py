"""Downloads the documents listed in kb/sources.yaml and saves their text to kb/docs/<id>.md.

Usage (from Backend/):  python -m scripts.fetch_kb [--force]
"""

import argparse
import io
import sys
import time
from pathlib import Path

import httpx
import trafilatura
import yaml
from pypdf import PdfReader

from app.services.labels import CROPS, DISEASES, GENERAL

KB_DIR = Path(__file__).resolve().parent.parent / "kb"
DOCS_DIR = KB_DIR / "docs"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AuraFarmKB/1.0; educational use)"}


def load_sources() -> list[dict]:
    sources = yaml.safe_load((KB_DIR / "sources.yaml").read_text())["sources"]
    for s in sources:
        if s["crop"] not in CROPS and s["crop"] != GENERAL:
            raise ValueError(f"{s['id']}: unknown crop {s['crop']!r}")
        if s["disease"] not in DISEASES and s["disease"] != GENERAL:
            raise ValueError(f"{s['id']}: unknown disease {s['disease']!r}")
    return sources


def extract_text(response: httpx.Response) -> tuple[str, str | None]:
    """Returns (text, title)."""
    content_type = response.headers.get("content-type", "")
    if "pdf" in content_type or response.url.path.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(response.content))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        title = (reader.metadata.title if reader.metadata else None) or None
        return text, title
    html = response.text
    text = trafilatura.extract(html, output_format="markdown", include_tables=True) or ""
    metadata = trafilatura.extract_metadata(html)
    return text, metadata.title if metadata else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-download documents that already exist")
    args = parser.parse_args()

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    failures = []
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        for source in load_sources():
            out = DOCS_DIR / f"{source['id']}.md"
            if out.exists() and not args.force:
                continue
            try:
                response = client.get(source["url"])
                response.raise_for_status()
                text, title = extract_text(response)
            except Exception as e:
                failures.append((source["id"], str(e)))
                print(f"FAIL  {source['id']}: {e}")
                continue
            if len(text.strip()) < 200:
                failures.append((source["id"], "too little text extracted"))
                print(f"FAIL  {source['id']}: too little text extracted")
                continue
            front_matter = {
                "id": source["id"],
                "title": title or source["id"],
                "source_url": source["url"],
                "source_org": source["org"],
                "crop": source["crop"],
                "disease": source["disease"],
            }
            out.write_text(f"---\n{yaml.safe_dump(front_matter, sort_keys=False)}---\n\n{text.strip()}\n")
            print(f"OK    {source['id']} ({len(text)} chars)")
            time.sleep(1)  # be polite to extension servers

    if failures:
        print(f"\n{len(failures)} source(s) failed; the rest were saved to {DOCS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
