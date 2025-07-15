import os
import json
import faiss
import numpy as np
from openai import AzureOpenAI
from utils.llm import call_llm  # existing LLM wrapper

# ─── Configuration ─────────────────────────────────────────────────────────
CATALOG_PATH    = "complete_component_catalog.json"
INDEX_PATH      = "components_chunked.faiss"
META_PATH       = "components_chunked_meta.json"

# Azure OpenAI settings
AZURE_ENDPOINT  = "https://ccm-product-agent.openai.azure.com"
AZURE_API_KEY   = "2Gq04Cva1b41axfHcPMCWPaws9OJw3zk3iHRcrrZ9IFsQFVKvSegJQQJ99BDACYeBjFXJ3w3AAABACOG9c66"
API_VER         = "2025-01-01-preview"
EMBED_MODEL     = "text-embedding-ada-002"
IDEATION_MODEL  = "gpt-4.1"
TOP_K           = 5

# ─── Azure OpenAI client for embeddings ────────────────────────────────────
embed_client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=API_VER,
)


def embed_text(text: str) -> list[float]:
    """Call Azure OpenAI embeddings on a single text chunk."""
    resp = embed_client.embeddings.create(
        model=EMBED_MODEL,
        input=text
    )
    return resp.data[0].embedding


def load_catalog() -> dict:
    """Load the full extracted catalog from JSON."""
    with open(CATALOG_PATH, "r") as f:
        return json.load(f)


# ─── Build FAISS index by chunking each PDF into windows ───────────────────
def build_faiss_index():
    catalog = load_catalog()
    metas, embs = [], []

    for title, rec in catalog.items():
        # flatten all list fields into one long string
        items = []
        for field in ("products", "components", "formulation", "raw_materials"):
            items.extend(rec.get(field, []))
        full_text = "  ".join(items)

        # slice into overlapping windows
        window_size, overlap = 2000, 200
        start = 0
        while start < len(full_text):
            chunk = full_text[start:start + window_size]
            emb = embed_text(chunk)
            embs.append(emb)
            metas.append({"title": title, "url": rec["url"]})
            start += window_size - overlap

    # build and save index
    arr = np.array(embs, dtype="float32")
    index = faiss.IndexFlatIP(arr.shape[1])
    index.add(arr)
    faiss.write_index(index, INDEX_PATH)
    with open(META_PATH, "w") as f:
        json.dump(metas, f, indent=2)

    return index, metas


def load_faiss_index():
    """Load an existing FAISS index and its metas."""
    index = faiss.read_index(INDEX_PATH)
    metas = json.load(open(META_PATH))
    return index, metas


# ─── Retrieve top-K unique PDFs for a query ────────────────────────────────
def get_product_components(query: str, top_k: int = TOP_K) -> list[dict]:
    if not os.path.exists(INDEX_PATH):
        index, metas = build_faiss_index()
    else:
        index, metas = load_faiss_index()

    q_emb = np.array([embed_text(query)], dtype="float32")
    _, I = index.search(q_emb, top_k * 5)  # over-fetch to dedupe

    seen, results = set(), []
    for idx in I[0]:
        meta = metas[idx]
        t = meta["title"]
        if t not in seen:
            seen.add(t)
            results.append(meta)
            if len(results) >= top_k:
                break

    return results


# ─── Ideation using your existing call_llm ────────────────────────────────
def ideate_with_products(user_prompt: str, existing_concepts: list[dict]) -> str:
    # 1) Get top-K relevant PDFs
    matches = get_product_components(user_prompt)
    # 1a) build set of existing titles for deduping
    existing_titles = {c.get("title", "").lower() for c in existing_concepts}

    # 2) Build retrieval block
    retrieval_block = "### Retrieved Products & Datasheets:\n" + "\n".join(
        f"- {m['title']}: {m['url']}" for m in matches
    )

    # 3) Load full catalog once, then gather allowed components
    catalog = load_catalog()
    all_comps = []
    for m in matches:
        all_comps.extend(catalog[m["title"]]["components"])
    unique_comps = sorted(set(all_comps))

    allowed_block = (
        "### Allowed Components (use **only** these):\n"
        + "\n".join(f"- {c}" for c in unique_comps)
    )
    # 3a) Tell the LLM which EXISTING concepts to avoid
    avoid_block = ""
    if existing_titles:
        avoid_block = (
            "### Avoid These Existing Concepts:\n"
            + "\n".join(f"- {t}" for t in sorted(existing_titles))
        )

    # 4) System & user prompts, positional args
    system = (
        "You are a product-ideation expert. Generate new, higher-R-value insulation concepts "
        "that use **only** the components listed below—do not suggest any others. "
        "And ensure your ideas **do not** duplicate any of the existing concepts provided."
    )
    # stitch together everything: retrieval, allowed components, what to avoid, then the user brief
    sections = [retrieval_block, allowed_block]
    if avoid_block:
        sections.append(avoid_block)
    sections.append(f"### Original Brief:\n{user_prompt}")
    full_user = "\n\n".join(sections)

    return call_llm(
        AZURE_ENDPOINT,
        IDEATION_MODEL,
        API_VER,
        system,
        full_user,
        api_key=AZURE_API_KEY
    )


# ─── CLI demo ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    prompt = input("\u26a1\ufe0f Enter your ideation prompt: ").strip()
    print("\n\ud83d\udca1 Generating concepts\u2026\n")
    print(ideate_with_products(prompt))
