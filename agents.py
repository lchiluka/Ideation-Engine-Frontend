# ---------------------------------------------------------------------------
# agents.py  –  definition of every specialist agent, model map & prompts
# ---------------------------------------------------------------------------
"""This module wires:

• **AGENT_MODEL_MAP**   – which Azure deployment each agent uses.
• **AGENT_CONFIG**      – role-specific prompt + schema reference.
• **Agent dataclass**   – unified `.act()` method that validates JSON.
• **AGENTS**            – dict factory {name → Agent instance} for easy import.

Down-stream code just does:
────────────────────────────────────────────────────────────────────────────
from agents import AGENTS
result = AGENTS["Scientific Research Agent 2"].act(problem, constraints)
"""

from __future__ import annotations

import json, logging
from dataclasses import dataclass
from typing import Dict, Tuple, Any, Coroutine
import jsonschema, asyncio

from config import AZURE_ENDPOINT, PRODUCTS_ENDPOINT, AZURE_OPENAI_KEY, PRODUCTS_OPENAI_KEY
from schemas import SCHEMA_PW, AGENT_JSON_SCHEMAS
from utils.llm import call_llm, extract_json, minimum_schema_prompt, call_llm_with_schema, call_llm_with_schema_async


# ===========================================================================
# 1.  Model Deployment Map  =================================================
# ===========================================================================

# 👉  Replace deployment names with what you created in Azure.
AGENT_MODEL_MAP: Dict[str, Tuple[str, str, str, str]] = {
    "Literature Review Agent":             (AZURE_ENDPOINT, "ccm-ric-o3",               "2025-01-01-preview", AZURE_OPENAI_KEY),
    "TRIZ Ideation Agent":                 (AZURE_ENDPOINT, "ccm-ric-o3",               "2025-01-01-preview", AZURE_OPENAI_KEY),
    "Scientific Research Agent 1":         (AZURE_ENDPOINT, "ccm-ric-gpt-4.5-preview",  "2024-10-21", AZURE_OPENAI_KEY),
    "Scientific Research Agent 2":         (AZURE_ENDPOINT, "ccm-ric-o3",               "2025-01-01-preview", AZURE_OPENAI_KEY),
    "Cross-Industry Translation Agent":    (AZURE_ENDPOINT, "ccm-ric-o3",               "2025-01-01-preview", AZURE_OPENAI_KEY),
    "Integrated Solutions Agent":          (AZURE_ENDPOINT, "ccm-ric-o3",               "2025-01-01-preview", AZURE_OPENAI_KEY),
    "Black Hat Thinker Agent":             (AZURE_ENDPOINT, "ccm-ric-o3",               "2025-01-01-preview", AZURE_OPENAI_KEY),
    "Self Critique Agent":                 (AZURE_ENDPOINT, "ccm-ric-o3",               "2025-01-01-preview", AZURE_OPENAI_KEY),
    "Proposal Writer Agent":               (AZURE_ENDPOINT, "ccm-ric-o3",               "2025-01-01-preview", AZURE_OPENAI_KEY),
    "Product Ideation Agent":              ("https://ccm-product-agent.openai.azure.com", "gpt-4.1",       "2025-01-01-preview", "2Gq04Cva1b41axfHcPMCWPaws9OJw3zk3iHRcrrZ9IFsQFVKvSegJQQJ99BDACYeBjFXJ3w3AAABACOG9c66"),
    "TRL Assessment":              (AZURE_ENDPOINT, "ccm-ric-o3", "2025-01-01-preview", AZURE_OPENAI_KEY),
    "Semantic Matcher":              (AZURE_ENDPOINT, "ccm-ric-o3", "2025-01-01-preview", AZURE_OPENAI_KEY)
}

# ===========================================================================
# 2.  Minimal role prompts  (edit to taste)  ===============================
# ===========================================================================
AGENT_CONFIG = {
    "TRIZ Ideation Agent": {
        "prompt": "You are a seasoned TRIZ specialist. Conduct a thorough contradiction analysis by identifying technical and physical contradictions, cite the top 5–10 TRIZ principles by number and name, and propose solutions using structured headings and bullets.",
        "schema": AGENT_JSON_SCHEMAS["TRIZ Ideation Agent"]
    },
    "Scientific Research Agent 1": {
        "prompt": "You are a visionary materials scientist specializing in polymers. Generate 5 radical, scientifically-grounded concepts with clear novelty reasoning, applications, and credible sources.",
        "schema": AGENT_JSON_SCHEMAS["Scientific Research Agent 1"]
    },
    "Scientific Research Agent 2": {
        "prompt": (
            "You are an expert in physics, chemistry, thermodynamics, mechanics, "
            "and manufacturability. For each concept, evaluate feasibility, "
            "provide qualitative reasoning, cost estimate, TRL with "
            "justification. Ground the TRL reasoning in real research and cite "
            "2–3 credible sources (journals, patents, or industry reports). "
            "Mention these sources in the `trl_reasoning` and list them in a "
            "`trl_citations` array."
        ),
        "schema": AGENT_JSON_SCHEMAS["Scientific Research Agent 2"]
    },
    "Cross-Industry Translation Agent": {
        "prompt": (
            "You are a cross-industry innovation scout. **Generate 10-15 novel solution concepts**.Find analogous problems "
            "in other fields, summarise the original solution and industry, then "
            "adapt that solution for roofing and building-envelope applications. "
            "List adaptation challenges and provide source URLs. Use insights "
            "from Scientific Research Agent 2 when helpful."
        ),
        "schema": AGENT_JSON_SCHEMAS["Cross-Industry Translation Agent"]
    },
    "Integrated Solutions Agent": {
        "prompt": "You are a systems integrator. Develop a multi-layer insulation blueprint: layer details, control strategies, metrics, and sources.",
        "schema": AGENT_JSON_SCHEMAS["Integrated Solutions Agent"]
    },
    "Black Hat Thinker Agent": {
        "prompt": "You are the devil's advocate performing FMEA. List failure modes, rank severity, probability, detectability, and recommend mitigations.",
        "schema": AGENT_JSON_SCHEMAS["Black Hat Thinker Agent"]
    },
    "Self Critique Agent": {
        "prompt": "You are the internal reviewer. Identify vagueness or unsupported claims, clarify assumptions, and suggest refinements.",
        "schema": AGENT_JSON_SCHEMAS["Self Critique Agent"]
    },
    "Product Ideation Agent": {
        "prompt": (
            "You are a product development specialist with direct access to our "
            "internal product datasheets. Using ONLY components and product names "
            "found in those datasheets, apply the SCAMPER framework to generate "
            "new product concepts. For each idea, list the SCAMPER actions and "
            "the exact components or product names referenced, and include a "
            "brief novelty note. Do not introduce materials or technologies that "
            "are not present in the datasheets." 
            "For each solution, after describing it, include a `references` array "
            "listing the relevant datasheet titles and their `datasheetUrl` "
            "from the retrieval results."
        ),
        "schema": AGENT_JSON_SCHEMAS["Product Ideation Agent"]
    },
    "TRL Assessment": {
        "prompt": "You determine the Technology Readiness Level of a concept based on the provided rubric and evidence.",
        "schema": AGENT_JSON_SCHEMAS["TRL Assessment"]
    }
}
# ─── agents.py  (put this right after you finish building AGENT_CONFIG) ───
AGENT_CONFIG.setdefault(                   # create the key if it’s missing
    "Literature Review Agent",
    {
        "prompt": "You are a scientific research librarian. Return one JSON "
                  "object with a `citations` array …",        # ← default text
        "schema": AGENT_JSON_SCHEMAS["Literature Review Agent"],
    },
)

# Now it’s safe to overwrite just the prompt or anything else ↓
AGENT_CONFIG["Literature Review Agent"]["prompt"] = (
    "You are a scientific research librarian. Return **one JSON object** with "
    "a `citations` array. Each element may be either a brief string *or* a detailed "
    "object containing title, journal, year, and PMID/Patent#."
)


AGENT_CONFIG["Proposal Writer Agent"] = {
    "prompt": minimum_schema_prompt(SCHEMA_PW),
    "schema": SCHEMA_PW,
}
AGENT_CONFIG["Scientific Research Agent 2"]["prompt"] += """
Add *two* narrative fields for every concept you output:
• **description** – 1 short paragraph (≈60 words) that explains the concept.
• **novelty_reasoning** – what makes it new or better, 1-2 sentences.
"""

# ===========================================================================
# 3.  Unified Agent class  ==================================================
# ===========================================================================

@dataclass
class Agent:
    name: str
    prompt: str
    schema: dict

    async def _act_async(self, user_concept: str, constraints_block: str = "") -> dict:
        endpoint, deployment, version, api_key = AGENT_MODEL_MAP[self.name]

        role_prompt = f"You are {self.name}. {self.prompt}\n{constraints_block}"

        obj = await call_llm_with_schema_async(
            endpoint,
            deployment,
            version,
            role_prompt,
            user_concept,
            self.schema,
            max_attempts=3,
            api_key=api_key
        )

        return obj

    def act(self, user_concept: str, constraints_block: str = "") -> dict | Coroutine[Any, Any, dict]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            return self._act_async(user_concept, constraints_block)

        return asyncio.run(self._act_async(user_concept, constraints_block))
# ---------------------------------------------------------------------------
# Convenience factory: dict[str, Agent]
# ---------------------------------------------------------------------------

AGENTS: Dict[str, Agent] = {
    name: Agent(name, cfg["prompt"], cfg["schema"]) for name, cfg in AGENT_CONFIG.items()
}

# agents.py  (after class Agent)
def _flatten_solution(sol: dict) -> dict:
    """
    Map each agent’s native keys → the unified columns your UI expects.
    """
    if "TRIZ_Principles" in sol:          # TRIZ Ideation Agent
        return {
            "Title": sol.get("Title") or sol.get("Name"),
            "description": "\n".join(sol.get("Architecture", "").splitlines()),
            "novelty_reasoning": None,
            "feasibility_reasoning": None,
            "cost_estimate": sol.get("CostImpact"),
            "trl":          sol.get("TRL"),
            "trl_reasoning": None,
            "severity":     None,
            "probability":  None,
        }
    if "novelty_reasoning" in sol:        # Sci Research 1
        return {
            "Title": sol.get("Title"),
            "description": sol.get("description"),
            "novelty_reasoning": sol.get("novelty_reasoning"),
        }
    if "feasibility_reasoning" in sol:    # Sci Research 2
        return {
            "Title": sol.get("Title"),
            "feasibility_reasoning": sol.get("feasibility_reasoning"),
            "cost_estimate": sol.get("cost_estimate"),
            "trl": sol.get("trl"),
            "trl_reasoning": sol.get("trl_reasoning"),
            "trl_citations": sol.get("trl_citations"),
        }
    if "severity" in sol:                 # Black-Hat
        return {
            "Title": sol.get("Title"),
            "severity": sol.get("severity"),
            "probability": sol.get("probability"),
        }
    if "suggestion" in sol:               # Self-Critique
        return {"Title": sol.get("Title"), "description": sol.get("suggestion")}
    if "scamper_steps" in sol:            # Product Ideation Agent
        return {
            "Title": sol.get("Title"),
            "description": sol.get("description"),
            "novelty_reasoning": sol.get("novelty_reasoning"),
            "components": sol.get("components"),

        }
    return {"Title": sol.get("Title")}    # fallback

# End of file
