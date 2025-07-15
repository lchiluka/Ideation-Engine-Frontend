# extract_components.py

import os
import json
import asyncio
from langdetect import detect, DetectorFactory
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from utils.llm import call_llm_with_schema_async, call_llm
from schemas import AGENT_JSON_SCHEMAS

# ─── Seed langdetect for consistency ────────────────────────────────────────
DetectorFactory.seed = 0

# ─── Configuration ─────────────────────────────────────────────────────────
import os
import streamlit as st

def _get(k: str, default=None):
    # first try st.secrets (deployed), then fall back to env‐vars (local .env)
    return st.secrets.get(k, os.getenv(k, default))

API_BASE_URL           = _get("API_BASE_URL")
AZURE_ENDPOINT         = _get("AZURE_ENDPOINT")
AZURE_OPENAI_KEY       = _get("AZURE_OPENAI_KEY")
OPENAI_API_KEY         = _get("OPENAI_API_KEY")
OPENAI_ENDPOINT        = _get("OPENAI_ENDPOINT")
PRODUCTS_ENDPOINT      = _get("PRODUCTS_ENDPOINT")
PRODUCTS_OPENAI_KEY    = _get("PRODUCTS_OPENAI_KEY")
SEARCH_ENDPOINT        = _get("SEARCH_ENDPOINT")
SEARCH_INDEX           = _get("SEARCH_INDEX")
SEARCH_KEY             = _get("SEARCH_KEY")
SERP_API_KEY           = _get("SERP_API_KEY")
# Fail fast if critical secrets are missing when imported by the main app.
PRIMARY_MODEL = "gpt-4.1" 
FALLBACK_MODEL  = "gpt-4o"
API_VER     = "2025-01-01-preview"
# ─── JSON Schema for extraction ─────────────────────────────────────────
# ─── JSON Schema for extraction ───────────────────────────────────────────
AGENT_JSON_SCHEMAS["Component Extraction"] = {
    "type": "object",
    "properties": {
        "products":       {"type": "array", "items": {"type": "string"}},
        "components":     {"type": "array", "items": {"type": "string"}},
        "formulation":    {"type": "array", "items": {"type": "string"}},
        "raw_materials":  {"type": "array", "items": {"type": "string"}},
    },
    "required": [],
    "additionalProperties": False,
    "anyOf": [
        {"required": ["products"]},
        {"required": ["components"]},
        {"required": ["formulation"]},
        {"required": ["raw_materials"]}
    ]
}

# ─── Azure Search client ─────────────────────────────────────────────────
search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name=SEARCH_INDEX,
    credential=AzureKeyCredential(SEARCH_KEY)
)

# ─── Helper: detect English text ──────────────────────────────────────────
def is_english(text: str) -> bool:
    try:
        return detect(text[:1000]) == "en"
    except:
        return False

# ─── Call LLM with schema, fallback to JSON parse ─────────────────────────
async def safe_extract(text: str) -> dict:
    schema = AGENT_JSON_SCHEMAS["Component Extraction"]
    prompt = (
        "You are a product-formulation expert. Below is datasheet text:\n\n"
        f"{text}\n\n"
        "Extract exactly JSON matching this schema, flag inferred items with '(D)':\n"
        f"{json.dumps(schema, indent=2)}"
    )
    # Schema-enforced extraction attempts
    for attempt in range(3):
        try:
            return await call_llm_with_schema_async(
                endpoint=OPENAI_ENDPOINT,
                deployment=PRIMARY_MODEL,
                version=API_VER,
                role_prompt="Component Extraction",
                user_prompt=prompt,
                schema=schema,
                max_attempts=1,
                api_key=OPENAI_API_KEY
            )
        except Exception as e:
            print(f"⚠️  Schema extraction failed (attempt {attempt+1}): {e}")
            await asyncio.sleep(1)
    # Fallback to plain text + JSON parse
    try:
        raw = call_llm(
            endpoint=OPENAI_ENDPOINT,
            deployment=FALLBACK_MODEL,
            version=API_VER,
            system="Return valid JSON only.",
            user=prompt,
            api_key=OPENAI_API_KEY
        )
        return extract_json(raw)
    except Exception as e:
        print(f"❌ Fallback parse failed: {e}")
        return {}

# ─── Extract per-PDF with overlapping windows ─────────────────────────────
async def extract_from_doc(doc: dict) -> dict | None:
    title   = doc.get("title") or doc.get("id", "<no-title>")
    url     = doc.get("url", "")
    content = doc.get("content", "")
    if not content or not is_english(content):
        return None

    window_size = 2000
    overlap     = 200
    comps, forms, raws, prods = [], [], [], []
    start = 0
    while start < len(content):
        window = content[start:start+window_size]
        res = await safe_extract(window)
        prods  += res.get("products", [])
        comps  += res.get("components", [])
        forms  += res.get("formulation", [])
        raws   += res.get("raw_materials", [])
        start += window_size - overlap

    return {
        "title":         title,
        "url":           url,
        "products":      sorted(set(prods)),
        "components":    sorted(set(comps)),
        "formulation":   sorted(set(forms)),
        "raw_materials": sorted(set(raws)),
    }

# ─── Main: parallel extraction, skip processed & non-English, write results immediately ─
async def main():
    catalog_file = "complete_component_catalog.json"
    catalog = json.load(open(catalog_file)) if os.path.exists(catalog_file) else {}
    processed = set(catalog.keys())
    total     = search_client.get_document_count()
    print(f"🔍 Index has {total} chunks; processed {len(processed)} PDFs.")

    # group chunks by PDF title
    by_title = {}
    page_size = 500
    for skip in range(0, total, page_size):
        batch = list(search_client.search(search_text="*", top=page_size, skip=skip))
        for d in batch:
            t = d.get("title") or d.get("id")
            by_title.setdefault(t, []).append(d)

    # build list of docs to do
    docs_to_do = []
    for title, chunks in by_title.items():
        if title in processed: 
            continue
        full_text = "".join(c["content"] for c in chunks)
        if not full_text or not is_english(full_text):
            continue
        docs_to_do.append((title, chunks))

    print(f"▶️ Scheduling {len(docs_to_do)} extraction tasks...")

    # concurrency limiter
    sem = asyncio.Semaphore(10)

    async def worker(title, chunks):
        async with sem:
            print(f"⏳ Starting {title}")
            entry = await extract_from_doc({
                "title":   title,
                "url":      chunks[0].get("url",""),
                "content":  "".join(c["content"] for c in chunks)
            })
            if entry:
                catalog[title] = entry
                with open(catalog_file, "w") as f:
                    json.dump(catalog, f, indent=2)
                print(f"  ✔️ Done {title}")

    tasks = [asyncio.create_task(worker(title, chunks))
             for title, chunks in docs_to_do]

    # wait and show progress
    for i, task in enumerate(asyncio.as_completed(tasks), 1):
        await task
        print(f"Progress: {i}/{len(tasks)}")

    print(f"✅ All done: {len(catalog)} PDFs in catalog.")


if __name__ == "__main__":
    asyncio.run(main())
