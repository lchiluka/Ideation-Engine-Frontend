# ---------------------------------------------------------------------------
# utils/llm.py  –  network helpers for LLM calls, SERP look‑ups, and JSON‑safe
# ---------------------------------------------------------------------------
"""Everything that talks to the outside world (Azure OpenAI & SerpAPI)
      plus a couple of robust text‑parsing helpers.

Usage:
────────────────────────────────────────────────────────────────────────────
from utils.llm import call_llm, serp_lookup, extract_json

raw = call_llm(endpoint, deployment, version, system_prompt, user_prompt)
json_obj = extract_json(raw)
serp_results = serp_lookup("roof insulation TRL 6", k=5)
"""

from __future__ import annotations

import json, logging, re, urllib3, requests, html
from typing import Any, List, Dict
from config import AZURE_OPENAI_KEY, SERP_API_KEY

urllib3.disable_warnings()

# ===========================================================================
# 🛠️  1.  Text‑sanitisation helpers  ========================================
# ===========================================================================

def ascii_safe(text: str | None) -> str:
    """Convert smart quotes / m‑dashes to ASCII; drop non‑ASCII remnants."""
    if text is None:
        return ""
    repl = {
        "\u2010": "-", "\u2011": "-", "\u2013": "-", "\u2014": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    }
    for k, v in repl.items():
        text = text.replace(k, v)
    return text.encode("ascii", "ignore").decode("ascii")


def safe_headers(hdrs: dict) -> dict:
    """Ensure every header value is ASCII‑clean so `requests` never complains."""
    return {k: ascii_safe(v) if isinstance(v, str) else v for k, v in hdrs.items()}

# ===========================================================================
# ✨  2.  Azure OpenAI chat wrapper  =========================================
# ===========================================================================
import time
from requests.exceptions import ReadTimeout

# ─── utils/llm.py  (REPLACE the existing call_llm function) ────────────────
def call_llm(endpoint, deployment, version, system_prompt, user_prompt, api_key=None) -> str:
    key = api_key or AZURE_OPENAI_KEY
    if not key:
        return "Error: Azure key missing"
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={version}"
    headers_raw = {
        "api-key": key,
        "Content-Type": "application/json",
    }
    headers = safe_headers(headers_raw)
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_completion_tokens": 15000,
    }
    resp = requests.post(url, headers=headers, json=payload, verify=False)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"].strip()
    logging.error(f"LLM fail {resp.status_code}: {resp.text}")
    return f"Error {resp.status_code}: {resp.text}"

# ===========================================================================
# 🔍  3.  Google SERP API helper  ===========================================
# ===========================================================================

def serp_lookup(query: str, k: int = 5) -> List[Dict[str, str]]:
    """Return up to *k* organic result dicts using SerpAPI (Google engine)."""
    if not SERP_API_KEY:
        logging.warning("SERP_API_KEY not set – skipping search for '%s'", query)
        return []
    params = {
        "engine": "google",
        "q":      query,
        "api_key": SERP_API_KEY,
        "num":    k,
    }
    try:
        r = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
        r.raise_for_status()
        return r.json().get("organic_results", [])
    except Exception as e:
        logging.error("SERP lookup failed: %s", e)
        return []

# ===========================================================================
# 🕵️‍♂️  4.  Robust JSON extractor  ==========================================
# ===========================================================================

def extract_json(blob: str) -> Any:
    """Return the first valid JSON object/array found in *blob*.

    Strips markdown fences, does brace‑count scanning so it survives extra
    prose the model might hallucinate.
    """
    txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", blob.strip(), flags=re.I | re.S)

    # locate first '{' or '['
    first_curly  = txt.find("{")
    first_square = txt.find("[")
    if first_curly == -1 and first_square == -1:
        raise ValueError("No JSON object/array found in text")

    start = first_curly if (first_curly != -1 and (first_curly < first_square or first_square == -1)) else first_square
    stack, end = [], None
    for i, ch in enumerate(txt[start:]):
        if ch in "[{":
            stack.append(ch)
        elif ch in "]}":
            if not stack:
                break
            stack.pop()
            if not stack:
                end = start + i + 1
                break
    if end is None:
        raise ValueError("Unbalanced braces/brackets in JSON blob")

    return json.loads(txt[start:end])



import textwrap

def minimum_schema_prompt(schema: dict) -> str:
    """
    Build a concise system-prompt that forces an LLM to
      • include every *required* key in the JSON schema
      • output exactly one JSON object (no markdown fences)
      • allow extra keys / nesting
    """
    required = ", ".join(schema.get("required", []))
    pretty   = json.dumps(schema, indent=2)

    prompt = f"""
    You are a **JSON-only** agent.

    1. Return exactly **one** JSON object – no markdown, no code fences.
    2. This object **must** contain at least these top-level keys:
       {required}
    3. Extra keys / nested detail are welcome, but never omit a required one.
    4. Invalid JSON will be rejected automatically.

    ### Reference schema (extra keys allowed)

    {pretty}
    """
    return textwrap.dedent(prompt).lstrip()
import json, logging, jsonschema, asyncio
from typing import Dict, Any

def call_llm_with_schema(
    endpoint: str,
    deployment: str,
    version: str,
    role_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
    max_attempts: int = 3,
    api_key: str | None = None,
) -> Dict[str, Any]:
    """
    Wrapper that keeps calling Azure until the reply validates
    against *schema* or max_attempts is reached.
    Returns the validated object (dict/list).
    Raises RuntimeError on repeated failure.
    """
    # 1) prepend the minimum-schema helper
    sys_prompt = minimum_schema_prompt(schema) + "\n" + role_prompt

    attempt = 1
    while attempt <= max_attempts:
        raw = call_llm(endpoint, deployment, version, sys_prompt, user_prompt, api_key)

        # strip fences & try to load JSON
        try:
            obj = extract_json(raw)
        except Exception as e:
            err = f"Attempt {attempt}: JSON parse error – {e}"
        else:
            try:
                jsonschema.validate(obj, schema)
                return obj                     # 🎉 success!
            except jsonschema.ValidationError as e:
                err = f"Attempt {attempt}: schema validation – {e}"

        logging.warning("%s; retrying…" % err)

        # ask the model to fix its own output
        fix_prompt = (
            "Your previous response did **not** validate against the schema.\n"
            f"Validation error:\n```\n{err}\n```\n\n"
            "Here is your prior JSON:\n"
            f"```\n{raw.strip()}\n```\n\n"
            "➡️  Return **exactly one** JSON object that satisfies the schema. "
            "No extra commentary."
        )
        user_prompt = fix_prompt               # next loop gets this prompt
        attempt += 1

    raise RuntimeError(
        f"{deployment}: failed to produce schema-valid JSON after {max_attempts} attempts"
    )


async def call_llm_with_schema_async(
    endpoint: str,
    deployment: str,
    version: str,
    role_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
    max_attempts: int = 3,
    api_key: str | None = None,
) -> Dict[str, Any]:
    """Async wrapper around :func:`call_llm_with_schema`."""
    return await asyncio.to_thread(
        call_llm_with_schema,
        endpoint,
        deployment,
        version,
        role_prompt,
        user_prompt,
        schema,
        max_attempts,
        api_key,
    )

import asyncio
from .llm import call_llm_with_schema_async

def call_llm_with_schema_sync(
    *,
    endpoint: str,
    deployment: str,
    version: str,
    role_prompt: str,
    user_prompt: str,
    schema: dict,
    api_key: str,
    **kwargs
) -> Any:
    """
    Synchronous wrapper around the async call_llm_with_schema_async.
    Passes through all parameters.
    """
    return asyncio.run(
        call_llm_with_schema_async(
            endpoint=endpoint,
            deployment=deployment,
            version=version,
            role_prompt=role_prompt,
            user_prompt=user_prompt,
            schema=schema,
            api_key=api_key,
            **kwargs,
        )
    )

# End of file
