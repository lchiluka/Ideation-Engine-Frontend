y# ---------------------------------------------------------------------------
# config.py  –  central constants & environment‑specific settings
# ---------------------------------------------------------------------------
"""All non‑secret, project‑wide constants live here.

Secrets such as the Azure OpenAI key are read from environment variables
so you never hard‑code credentials.  Adjust your `.env` / OS envvars or use
Streamlit's Secrets manager when deploying.
"""

from __future__ import annotations
import os

# ===========================================================================
# 🔐  Endpoints & API keys (read from env)  =================================
# ===========================================================================

def _get(key: str, default=None):
    # first try st.secrets (deployed), then fall back to env‐vars (local .env)
    return os.getenv(key, default)

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


if not AZURE_ENDPOINT or not AZURE_OPENAI_KEY:
    import warnings
    warnings.warn(
        "AZURE_ENDPOINT or AZURE_OPENAI_KEY not set – LLM calls will fail. "
        "Use `export AZURE_ENDPOINT=...` and `export AZURE_OPENAI_KEY=...`.")

if not PRODUCTS_ENDPOINT or not PRODUCTS_OPENAI_KEY:
    import warnings
    warnings.warn("PRODUCTS_ENDPOINT or PRODUCTS_OPENAI_KEY not set – Product Ideation Agent will fail. Use `export PRODUCTS_ENDPOINT=...` and `export PRODUCTS_OPENAI_KEY=...`.")
# ===========================================================================
# 📋  Pre‑defined agent workflows  ==========================================
# ===========================================================================

WORKFLOWS: dict[str, list[str]] = {
    "TRIZ Based Ideation": [
        "Literature Review Agent",
        "Product Ideation Agent",
        "TRIZ Ideation Agent",
        "Scientific Research Agent 1",
        "Scientific Research Agent 2",
        "Black Hat Thinker Agent",
        "Self Critique Agent",
    ],
    "Cross-Industry Ideation": [
        "Cross-Industry Translation Agent", 
        "Scientific Research Agent 2",
        "Black Hat Thinker Agent",
        "Self Critique Agent",
    ],
    "Integrated Solutions Ideation": [
        "Product Ideation Agent",
        "Integrated Solutions Agent",
        "Scientific Research Agent 1",
        "Scientific Research Agent 2",
        "Black Hat Thinker Agent",
        "Self Critique Agent",
    ],
}
# ------------------------------------------------------------------
# Agents grouped by phase (used by ideate_and_refactor in app.py)
# ------------------------------------------------------------------
# Union of all agents capable of generating initial concepts. Specific
# workflows will select a relevant subset of these.
IDEATION_AGENTS = [
    "TRIZ Ideation Agent",
    "Cross-Industry Translation Agent",
    "Integrated Solutions Agent",
    "Scientific Research Agent 1",
    "Scientific Research Agent 2",
    "Product Ideation Agent",
]

REVIEW_AGENTS = [           # must accept a list[dict] of solutions
    "Black Hat Thinker Agent",
    "Self Critique Agent",
]

# ===========================================================================
# Misc global settings  (edit as needed)  ===================================
# ===========================================================================

DEFAULT_COST_UNIT   = "USD/ft²"
DEFAULT_TARGET_COST = 15.0   # same unit as above
MIN_ACCEPTABLE_TRL  = 4

# ===========================================================================
# SECTION DEPENDENCIES FOR REGENERATION (edit as needed)  ===================================
# ===========================================================================
# dependencies.py  (import anywhere)
SECTION_DEPENDENCIES: dict[str, list[str]] = {
    # ───────────────────────────────────────────────────────────────────────
    # Foundation layers → everything that follows
    # ───────────────────────────────────────────────────────────────────────
    "problem_statement": [
        "concept_overview",          # framing may shift
        "executive_summary",
        "title",
    ],
    "concept_overview": [
        "technical_details",
        "performance_targets",
        "manufacturing_process",
        "sustainability",
        "applications",
        "executive_summary",
    ],

    # ───────────────────────────────────────────────────────────────────────
    # Core technical definition
    # ───────────────────────────────────────────────────────────────────────
    "technical_details": [
        "performance_targets",       # new materials → new KPIs
        "manufacturing_process",     # process must suit materials / structure
        "cost_feasibility",          # BOM & process drive cost
        "risks_mitigations",         # new failure modes
        "sustainability",            # LCA numbers change
        "validation_plan",           # new coupons / tests
        "work_plan",                 # tasks realign
        "kpi_table",                 # targets maybe re-tuned
        "executive_summary",
    ],
    "manufacturing_process": [
        "cost_feasibility",          # capex / throughput shift
        "risks_mitigations",         # process FMEA
        "work_plan",                 # scale-up tasks
        "validation_plan",           # pilot‐line samples vs lab
        "kpi_table",
        "executive_summary",
    ],
    "performance_targets": [
        "kpi_table",                 # roll-up numbers
        "validation_plan",           # test matrix
        "executive_summary",
        "technical_details",
        "concept_overview",
        "manufacturing_process"
    ],

    # ───────────────────────────────────────────────────────────────────────
    # Economics & risk
    # ───────────────────────────────────────────────────────────────────────
    "cost_feasibility": [
        "work_plan",                 # budget / timeline gating
        "kpi_table",                 # $/ft² target row
        "executive_summary",
    ],
    "risks_mitigations": [
        "work_plan",                 # mitigation tasks
        "executive_summary",
    ],

    # ───────────────────────────────────────────────────────────────────────
    # Sustainability & market fit
    # ───────────────────────────────────────────────────────────────────────
    "sustainability": [
        "executive_summary",
        "applications",              # green-building credits etc.
    ],
    "applications": [
        "executive_summary",
        "work_plan",                 # pilot / field-trial tasks
    ],

    # ───────────────────────────────────────────────────────────────────────
    # Project planning layers
    # ───────────────────────────────────────────────────────────────────────
    "work_plan": [
        "validation_plan",           # test phases align with tasks
        "kpi_table",
        "executive_summary",
    ],
    "validation_plan": [
        "kpi_table",
        "executive_summary",
    ],

    # ───────────────────────────────────────────────────────────────────────
    # Summaries – always rebuild last
    # ───────────────────────────────────────────────────────────────────────
    "kpi_table":          ["executive_summary"],
    "ip_landscape":       ["executive_summary"],
    "references":         ["executive_summary"],

    # title & executive_summary depend on almost everything; handled globally
}


# End of file
