"""Functions to assess TRL using retrieval-augmented generation."""
from __future__ import annotations

import asyncio
import textwrap
from typing import Tuple, List, Dict

from utils.evidence import gather_evidence, sanitize_snippet
from utils.trl import load_trl_rubric
from utils.llm import call_llm_with_schema
from schemas import AGENT_JSON_SCHEMAS
from config import AZURE_ENDPOINT, AZURE_OPENAI_KEY

# Use a small deployment by default
DEPLOYMENT = "ccm-ric-o3"
VERSION = "2025-01-01-preview"

async def assess_trl_async(topic: str) -> Tuple[Dict, List[Dict]]:
    rubric = load_trl_rubric()
    evidence = await gather_evidence(topic)

    evidence_lines = []
    for i, ev in enumerate(evidence, 1):
        snippet = sanitize_snippet(ev['snippet'])
        evidence_lines.append(f"[{i}] {snippet} ({ev['source_url']})")
    evidence_block = "\n".join(evidence_lines)

    schema = AGENT_JSON_SCHEMAS.setdefault(
        "TRL Assessment", {
            "type": "object",
            "properties": {
                "trl": {"type": "string"},
                "justification": {"type": "string"},
                "citations": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["trl", "justification", "citations"],
        }
    )

    sys_p = textwrap.dedent(
        """
        You are an impartial expert assessing technology readiness.
        Reply in JSON only, conforming to the provided schema.
        """
    ).strip()

    user_p = textwrap.dedent(
        f"""
        ### TRL rubric
        {rubric}

        ### Topic
        {topic}

        ### Evidence
        {evidence_block}
        """
    )

    result = call_llm_with_schema(
        AZURE_ENDPOINT,
        DEPLOYMENT,
        VERSION,
        sys_p,
        user_p,
        schema,
        api_key=AZURE_OPENAI_KEY,
    )

    return result, evidence

def assess_trl(topic: str) -> Tuple[Dict, List[Dict]]:
    return asyncio.run(assess_trl_async(topic))
