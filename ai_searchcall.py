from agents import AGENT_CONFIG
from schemas import AGENT_JSON_SCHEMAS
import re
from difflib import SequenceMatcher
from utils.llm import minimum_schema_prompt, extract_json, call_llm
from product_ideation_agent import (
    get_product_components,
    load_catalog,
    AZURE_ENDPOINT,
    AZURE_API_KEY,
    API_VER,
    IDEATION_MODEL,
)

def call_product_ideation_with_search(
    user_concept: str,
    existing_concepts: list[dict],
    top_k: int | None = None
) -> dict:
    """
    Return structured product ideas grounded in retrieved datasheets,
    avoiding any titles similar to those in existing_concepts.
    If top_k is provided, instruct the model to generate up to that many concepts.
    """
    # ── normalize helper ─────────────────────────────────────────────────
    def _normalize_title(t: str) -> str:
        return re.sub(r'[^a-z0-9]', '', t.lower())

    # ── 1) Build JSON-schema system prompt ────────────────────────────────
    schema = AGENT_JSON_SCHEMAS["Product Ideation Agent"]
    system_prompt = minimum_schema_prompt(schema) + "\n" + AGENT_CONFIG["Product Ideation Agent"]["prompt"]

    # ── 2) Retrieval + allowed components ──────────────────────────────────
    matches = get_product_components(user_concept)
    retrieval_block = "### Retrieved Products & Datasheets:\n" + "\n".join(
        f"- {m['title']}: {m['url']}" for m in matches
    )
    catalog = load_catalog()
    all_comps = []
    for m in matches:
        all_comps.extend(catalog[m["title"]]["components"])
    allowed_block = (
        "### Allowed Components (use **only** these):\n"
        + "\n".join(f"- {c}" for c in sorted(set(all_comps)))
    )

    # ── 2a) Build "avoid" block ─────────────────────────────────────────
    titles = [c.get("title", "") for c in existing_concepts if c.get("title")]
    avoid_block = ""
    if titles:
        avoid_block = (
            "### Avoid these existing concepts (do NOT re-generate):\n"
            + "\n".join(f"- {t}" for t in titles)
        )

    # ── 3) Build count directive ─────────────────────────────────────────
    count_block = ""
    if top_k:
        count_block = f"### Generate up to {top_k} novel concepts."

    # ── 4) Stitch the final user prompt ───────────────────────────────────
    parts = [count_block, retrieval_block, allowed_block]
    if avoid_block:
        parts.append(avoid_block)
    parts.append(f"### Original Brief:\n{user_concept}")
    user_prompt = "\n\n".join(p for p in parts if p)

    # ── 5) Call the LLM ─────────────────────────────────────────────────
    raw = call_llm(
        AZURE_ENDPOINT,
        IDEATION_MODEL,
        API_VER,
        system_prompt,
        user_prompt,
        api_key=AZURE_API_KEY,
    )

    # ── 6) Try to extract JSON, with quick repair if needed ─────────────
    try:
        result = extract_json(raw)
    except Exception:
        repaired = re.sub(r'"\s+"', '", "', raw)
        try:
            result = extract_json(repaired)
        except Exception as e:
            import logging
            logging.error("JSON extraction failed after repair: %s\nRaw:\n%s", e, raw)
            result = {"solutions": []}

    # Ensure solutions key exists as list
    if not isinstance(result.get("solutions"), list):
        result["solutions"] = []

    return result