# ---------------------------------------------------------------------------
# app.py – Streamlit front-end for Agentic Ideation Studio (schema-safe edition)
# ---------------------------------------------------------------------------
from __future__ import annotations


import streamlit as st
from pathlib import Path
import base64

st.set_page_config(
    page_title="Agentic Ideation Studio – Carlisle",
    page_icon="images/carlisle_logo.jpg",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 1) Read & Base64-encode your logo (unchanged)
_logo_path = Path(__file__).parent / "images" / "carlisle_logo.jpg"
_logo_data = base64.b64encode(_logo_path.read_bytes()).decode("utf-8")
_logo_uri  = f"data:image/jpeg;base64,{_logo_data}"

st.markdown(f"""
  <style>
    :root {{ --banner-height: 100px; }}

    /* Hide Streamlit’s default header & toolbar */
    [data-testid="stToolbar"],
    [data-testid="stHeader"] {{
      display: none !important;
      height: 0 !important;
      margin: 0 !important;
      padding: 0 !important;
    }}

    /* Your custom banner */
    .banner {{
      position: fixed !important;
      top: 0; left: 0; right: 0;
      height: var(--banner-height) !important;
      background-color: #003366;
      display: flex;
      align-items: center;
      padding: 0 24px;
      z-index: 2000 !important;            /* ABOVE everything else */
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}

    /* Push the app content down under your banner */
    .main .block-container {{
      padding-top: var(--banner-height) !important;
    }}

    /* Sidebar starts below the banner */
    [data-testid="stSidebar"] {{
      position: fixed !important;
      top: var(--banner-height) !important;
      height: calc(100% - var(--banner-height)) !important;
      overflow: visible !important;
      z-index: 1000 !important;
    }}

    /* Your other CSS: background stripes, DataFrame header tint, button styling… */
    body, [data-testid="stAppViewContainer"] {{
      background-color: #F2F2F2 !important;
    }}
    body::before {{
      content: "";
      position: fixed; top: 0; left: 0;
      width:100%; height:100%;
      background-image:
        repeating-linear-gradient(
          135deg,
          rgba(0,75,135,0.05) 0px,
          rgba(0,75,135,0.05) 1px,
          transparent 1px,
          transparent 20px
        );
      pointer-events: none; z-index: -1;
    }}
    .stDataFrame thead th {{
      background-color: #004B87 !important;
      color: white !important;
    }}
    .stButton>button {{
      background-color: #004B87;
      color: white;
      border-radius: 4px;
      padding: 0.5em 1em;
    }}
    .stButton>button:hover {{
      background-color: #003366;
    }}
    /* …any other <style> blocks you had… */
  </style>

  <div class="banner">
    <img src="{_logo_uri}" alt="Carlisle Logo" height="50" style="margin-right:1rem;">
    <h1 style="flex:1; color:white; margin:0; font-size:2rem; text-align:center;">
      Agentic Ideation Studio
    </h1>
  </div>
""", unsafe_allow_html=True)

st.markdown("""
<style>
  :root {
    /* banner height */
    --banner-h: 100px;
    /* sidebar widths */
    --sidebar-w: 16rem;    /* expanded width */
    --sidebar-w-c: 3rem;   /* collapsed gutter */
  }

  /* 1) Neutralize Streamlit’s built-in slide-out/margin */
  section[data-testid="stSidebar"] {
    transform: none !important;
    margin-left: 0      !important;
    transition: none    !important;
  }

  /* 2) Position expanded vs. collapsed under your banner */
  section[data-testid="stSidebar"][aria-expanded="true"] {
    position: fixed     !important;
    top:      var(--banner-h) !important;
    left:     0               !important;
    width:    var(--sidebar-w)   !important;
    height:   calc(100% - var(--banner-h)) !important;
    overflow: visible    !important;
    z-index:  1000       !important;
  }
  section[data-testid="stSidebar"][aria-expanded="false"] {
    position: fixed     !important;
    top:      var(--banner-h) !important;
    left:     0               !important;
    width:    var(--sidebar-w-c) !important;
    height:   calc(100% - var(--banner-h)) !important;
    overflow: visible    !important;
    z-index:  1000       !important;
  }

  /* 3) Shift the main app container to match the sidebar width */
  div[data-testid="stAppViewContainer"] {
    margin-left: var(--sidebar-w) !important;
    transition: margin-left .2s ease !important;
  }
  section[data-testid="stSidebar"][aria-expanded="false"]
    ~ div[data-testid="stAppViewContainer"] {
    margin-left: var(--sidebar-w-c) !important;
  }

  /* 4) Always show & pin the collapse/expand buttons */
  button[aria-label="Collapse sidebar"],
  button[aria-label="Expand sidebar"] {
    opacity: 1          !important;
    visibility: visible !important;
    pointer-events: all !important;
    background: none    !important;
    border: none        !important;
    position: fixed     !important;
    top:      calc(var(--banner-h) + 0.5rem) !important;
    left:     0.5rem    !important;
    z-index:  2000      !important;
    cursor:   pointer   !important;
  }
</style>
""", unsafe_allow_html=True)

import streamlit as st
import sys, inspect, json, time, logging, itertools
from io import BytesIO
from typing import List, Dict, Any

import pandas as pd
import deepdiff  # pip install deepdiff
import requests
import os
from config import WORKFLOWS, DEFAULT_COST_UNIT, DEFAULT_TARGET_COST, MIN_ACCEPTABLE_TRL
from config import SECTION_DEPENDENCIES
from agents import AGENTS
from utils.pptx_export import build_pptx_from_df
from utils.pptx_import import read_concept_cards
from utils.docx_export import build_docx_report
from utils.pptx_import import read_concept_cards
from utils.proposal_editor import ProposalEditor
from utils.llm import serp_lookup
from utils.trl_assessor import assess_trl_async, load_trl_rubric
from utils.evidence import gather_evidence, sanitize_snippet
from schemas import AGENT_JSON_SCHEMAS
from agents import AGENT_MODEL_MAP
from utils.llm import call_llm_with_schema_async
from ai_searchcall import call_product_ideation_with_search
import logging
import streamlit as st
from pathlib import Path
import base64

# ───────────────────────────────────────────────────────────────────────
# ─── Initialise session_state keys to sane defaults ────────────────────────
st.session_state.setdefault("generate", False)
st.session_state.setdefault("current_problem", "")
st.session_state.setdefault("df_existing", None)
st.session_state.setdefault("df_to_process", None)
st.session_state.setdefault("stage", "awaiting_concept")
st.session_state.setdefault("solutions_df", pd.DataFrame())
st.session_state.setdefault("chat", [])
st.session_state.setdefault("hist_concepts", {})
st.session_state.setdefault("show_export_hint", False)
st.session_state.setdefault("df_ppt", None)    # ← new
# ─────────────────────────────────────────────────────────────────────────────
# API config for FastAPI/Postgres back end
# ─────────────────────────────────────────────────────────────────────────────
API_BASE_URL =  "https://carlisle-ideation-engine-backend.azurewebsites.net"

def get_concepts_for(problem: str) -> list[dict]:
    try:
        r = requests.get(f"{API_BASE_URL}/concepts", params={"problem_statement": problem})
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.error(f"Error fetching concepts: {e}")
        return []


import requests

def get_similar_concepts(problem: str, top_k: int = 50) -> list[dict]:
    """Return concepts whose stored problem statements semantically match."""
    try:
        r = requests.get(
            f"{API_BASE_URL}/concepts/similar",
            params={"problem_statement": problem, "top_k": top_k},
        )
        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            # log the real JSON error message
            logging.error("GET /concepts/similar failed: %s\nResponse body: %s",
                          http_err, r.text)
            return []  # or re-raise if you prefer to see it crash
        return r.json()
    except Exception as e:
        logging.error(f"Error fetching similar concepts: {e}", exc_info=True)
        return []


logger = logging.getLogger(__name__)

def save_concepts(problem: str, concepts: list[dict]) -> tuple[bool,int,str]:
    workflow = st.session_state.selected_workflow
    payload = []
    for row in concepts:
        base = {
            "agent": row.get("agent"),
            "title": row.get("title"),
            "description": row.get("description"),
            "problem_statement": problem,
        }
        if workflow == "Cross-Industry Ideation":
            base["industry"]              = row.get("Industry")
            base["original_solution"]     = row.get("Original Solution")
            base["adaptation_challenges"] = row.get("Adaptation Challenges")
        else:
            base["novelty_reasoning"]     = row.get("novelty_reasoning")
            base["feasibility_reasoning"] = row.get("feasibility_reasoning")
            base["cost_estimate"]         = row.get("cost_estimate")
        payload.append(base)

        # ⬇️ NEW: include everything else your Pydantic schema expects ⬇️
        base["trl"]                         = row.get("trl")
        base["trl_reasoning"]               = row.get("trl_reasoning")
        base["trl_citations"]               = row.get("trl_citations")
        base["validated_trl"]               = row.get("validated_trl")
        base["validated_trl_reasoning"]     = row.get("validated_trl_reasoning")
        base["validated_trl_citations"]     = row.get("validated_trl_citations")
        base["components"]                  = row.get("components")
        base["references"]                  = row.get("references")
        base["constructive_critique"]       = row.get("constructive_critique")

    wf_param = "cross-industry" if workflow == "Cross-Industry Ideation" else "traditional"
    url = f"{API_BASE_URL}/concepts?workflow={wf_param}"

    try:
        r = requests.post(url, json=payload)
        body = r.text
        if not r.ok:
            # show full validation error and what we sent
            st.error(f"❌ Save failed (status={r.status_code})")
            try:
                # if JSON, pretty-print the list of errors
                st.json(r.json())
            except:
                st.write(body)
            st.warning("Payload was:")
            st.json(payload)
            return False, r.status_code, body

        logger.info("POST /concepts → %s\n%s", r.status_code, body)
        return True, r.status_code, body

    except Exception as e:
        logger.error("Exception posting concepts: %s", e, exc_info=True)
        st.error(f"❌ Exception posting concepts: {e}")
        return False, None, str(e)

# ---------------------------------------------------------------------------
# app.py  (put these right after the imports, before _create_proposal_draft)
# ---------------------------------------------------------------------------

from utils.llm import call_llm_with_schema_sync

# —————————————————————————————————————
# LLM‐based Problem Matching Helpers
# —————————————————————————————————————

def fetch_all_problems() -> list[str]:
    try:
        resp = requests.get(f"{API_BASE_URL}/problems")
        resp.raise_for_status()
        return [p["problem_statement"] for p in resp.json()]
    except Exception as e:
        logging.error("Could not fetch all problems:", e)
        return []

def get_similar_problems_via_llm(new_problem: str, top_k: int = 5) -> list[dict]:
    existing = fetch_all_problems()
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "problem_statement": {"type": "string"},
                "score": {"type": "number", "minimum": 0, "maximum": 1}
            },
            "required": ["problem_statement", "score"]
        }
    }
    system_prompt = """
You are an expert at comparing engineering problem statements semantically.
Given a new problem and a list of historical problems, return the top_k historical
problems most relevant to the new one, ordered by descending relevance score (0–1).
Output MUST be valid JSON matching the provided schema.
"""
    user_prompt = json.dumps({
        "new_problem": new_problem,
        "existing_problems": existing,
        "top_k": top_k
    })
    try:
        return call_llm_with_schema_sync(
            endpoint=AGENT_MODEL_MAP["Semantic Matcher"][0],
            deployment=AGENT_MODEL_MAP["Semantic Matcher"][1],
            version=AGENT_MODEL_MAP["Semantic Matcher"][2],
            role_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
            api_key=AGENT_MODEL_MAP["Semantic Matcher"][3],
        )
    except Exception as e:
        logging.error("LLM semantic-match failed:", e)
        return []
def render_concept_cards(df: pd.DataFrame, select_key_prefix: str, cards_per_row: int = 4):
    """
    Render each row of df as a scrollable card grid, with:
      - a Streamlit checkbox for Select/Deselect in the footer
      - an Expand button in the footer
      - full DISPLAY_COLS content in labelled sections
      - fixed height + internal scrolling
      - card border and background color based on the agent
    """
    border_colors = {
        "Scientific Research Agent 1": "#1E90FF",
        "Scientific Research Agent 2": "#32CD32",
        "Product Ideation Agent": "#FFD700",
        "Self Critique Agent": "#800080",
        "TRIZ Ideation Agent": "#FF69B4",
    }
    background_colors = {
        "Scientific Research Agent 1": "#E6F2FF",
        "Scientific Research Agent 2": "#E8FAE8",
        "Product Ideation Agent": "#FFF9E6",
        "Self Critique Agent": "#FFE6F0",
        "TRIZ Ideation Agent": "#F0E6F0",
    }

    # Keep track of historical keys if any
    hist_keys = list(st.session_state.get("hist_concepts", {}).keys())

    # Reset index so we know each card’s original df index
    df = df.reset_index(drop=False)

    for start in range(0, len(df), cards_per_row):
        slice_df = df.iloc[start : start + cards_per_row]
        cols = st.columns(len(slice_df))

        for col, (_, row) in zip(cols, slice_df.iterrows()):
            orig_idx = row["index"]
            agent    = row.get("agent", "")
            border   = border_colors.get(agent, "#CCCCCC")
            bg       = background_colors.get(agent, "#FFFFFF")

            def s(field):
                return str(row.get(field, "")).replace("\n", "<br/>")

            # Begin card
            with col:
                st.markdown(f"""
                <div class="concept-card" style="border-left:4px solid {border}; background-color:{bg};">
                  <div class="concept-card-header">
                    <h4 style="margin:0">{s('title')}</h4>
                    <small style="color:#666">Agent: {agent} | Sim: {row.get('similarity',0):.2f}</small>
                  </div>
                  <div class="concept-card-body">
                    <div class="concept-card-section"><span class="concept-card-label">Overview</span><div>{s('description')}</div></div>
                    <div class="concept-card-section"><span class="concept-card-label">Novelty</span><div>{s('novelty_reasoning')}</div></div>
                    <div class="concept-card-section"><span class="concept-card-label">Feasibility</span><div>{s('feasibility_reasoning')}</div></div>
                    <div class="concept-card-section"><span class="concept-card-label">Components</span><div>{s('components')}</div></div>
                    <div class="concept-card-section"><span class="concept-card-label">References</span><div>{s('references')}</div></div>
                    <div class="concept-card-section"><span class="concept-card-label">Self‐Critique</span><div>{s('constructive_critique')}</div></div>
                    <div class="concept-card-section"><span class="concept-card-label">Initial TRL</span><div>{s('trl')} — {s('trl_reasoning')}</div><div><em>Citations:</em> {s('trl_citations')}</div></div>
                    <div class="concept-card-section"><span class="concept-card-label">Validated TRL</span><div>{s('validated_trl')} — {s('validated_trl_reasoning')}</div><div><em>Citations:</em> {s('validated_trl_citations')}</div></div>
                    <div class="concept-card-section"><span class="concept-card-label">Cost</span><div><strong>{s('cost_estimate')}</strong></div></div>
                  </div>
                  <div class="concept-card-footer">
                """, unsafe_allow_html=True)

                # Footer layout
                col1, col2 = st.columns([1,1])
                checkbox_key = f"chk_{select_key_prefix}_{orig_idx}"
                button_key   = f"exp_{select_key_prefix}_{orig_idx}"

                # 1) figure out the *current* selection state
                if select_key_prefix.startswith("existing"):
                    current = st.session_state.df_existing.at[orig_idx, "__select__"]
                elif select_key_prefix.startswith("new"):
                    current = st.session_state.df_to_process.at[orig_idx, "__select__"]
                elif select_key_prefix == "ppt":
                    current = st.session_state.df_ppt.at[orig_idx, "__select__"]
                else:
                    grp     = int(select_key_prefix.split("_")[-1])
                    problem = hist_keys[grp]
                    current = st.session_state.hist_concepts[problem][orig_idx].get("__select__", False)

                # 2) render the checkbox
                checked = col1.checkbox("Select", key=checkbox_key, value=current)
                if checked != current:
                    # write back into the right store
                    if select_key_prefix.startswith("existing"):
                        st.session_state.df_existing.at[orig_idx, "__select__"] = checked
                    elif select_key_prefix.startswith("new"):
                        st.session_state.df_to_process.at[orig_idx, "__select__"] = checked
                    elif select_key_prefix == "ppt":
                        st.session_state.df_ppt.at[orig_idx, "__select__"] = checked
                    else:
                        st.session_state.hist_concepts[problem][orig_idx]["__select__"] = checked
                    # immediately rerun so Table view picks it up
                    try:
                        st.rerun()
                    except AttributeError:
                        st.rerun()

                # 3) expand button
                if col2.button("Expand", key=button_key):
                    st.session_state["expanded_prefix"] = select_key_prefix
                    st.session_state["expanded_card"]  = orig_idx
                    try:
                        st.rerun()
                    except AttributeError:
                        st.rerun()

                # close card
                st.markdown("</div></div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# Layout tuning – wide page and tighter side paddings
# ──────────────────────────────────────────────────────────────
# ── make the main block as wide as the viewport ───────────
st.markdown(
    """
<style>
/* remove Streamlit’s hard-coded width constraint */
[data-testid="stAppViewContainer"] .main .block-container {
    max-width: 100% !important;
    padding-left: 0.5rem;
    padding-right: 0.5rem;
}
/* every HTML preview iframe should use the full column width */
iframe { width: 100% !important; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    div[data-testid='stPopoverTarget'] {
        position: fixed;
        bottom: 1rem;
        right: 1rem;
        z-index: 1000;
    }
    div[data-testid='stPopoverContent'] {
        width: 360px;
        max-height: 70vh;
        overflow-y: auto;

    }
    </style>
    """,
    unsafe_allow_html=True,
)
# ─── Dark-mode toggle ────────────────────────────────────────────────
dark_mode = st.sidebar.checkbox("🌙 Dark mode", value=False)
if dark_mode:
    st.markdown(
        """
        <style>
          /* Invert everything… */
          :root { filter: invert(0.9) hue-rotate(180deg) !important; }
          /* …but keep images/videos readable */
          img, video, iframe { filter: invert(1) hue-rotate(180deg) !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
# ──────────────────────────────────────────────────────────────────────
# 1) Tweak your CSS (add right after your existing <style> block)
st.markdown("""
<style>
/* overall card */
.concept-card {
  position: relative;            /* allow footer to be absolutely positioned */
  border: 1px solid #ddd;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  height: 350px;
  background: #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 1rem;
  overflow: hidden;              /* clip any overflow */
}

/* header */
.concept-card-header {
  padding: 0.5rem;
  border-bottom: 1px solid #eee;
}

/* body scroll region */
.concept-card-body {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

/* labelled sections */
.concept-card-section {
  margin-bottom: 0.75rem;
}
.concept-card-label {
  font-weight: 600;
  margin-bottom: 0.25rem;
  display: block;
}

/* footer sits on top of the card content, at its bottom edge */
.concept-card-footer {
  position: absolute;
  left: 0.5rem;
  right: 0.5rem;
  bottom: 0.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  /* optional subtle backdrop */
  background: rgba(255,255,255,0.8);
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
}

/* hide any default overflow on the footer row */
.concept-card-footer > * {
  overflow: visible;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
def _ensure_helper_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure helper columns exist and contain sane defaults."""
    if "vote" in df.columns:
        df = df.drop(columns=["vote"])  # deprecated
    if "__select__" not in df.columns:
        df["__select__"] = False
    df["__select__"] = df["__select__"].fillna(False).astype(bool)
    if "similarity" not in df.columns:
        df["similarity"] = 0.0
    df["similarity"] = df["similarity"].fillna(0.0).astype(float)
    # ensure references column always exists (even if empty)
    # ensure _all_ DISPLAY_COLS exist so st.dataframe(df[DISPLAY_COLS]) never KeyErrors
    for col in DISPLAY_COLS:
        if col not in df.columns:
            # choose a sensible default: empty string for text-like, None otherwise
            df[col] = None

    return df


# Columns shown in the interactive solutions table
DISPLAY_COLS = [
    "similarity",
    "agent",
    "original_title",
    "title",
    "description",
    "novelty_reasoning",
    "feasibility_reasoning",
    "cost_estimate",
    "trl",
    "trl_reasoning",
    "trl_citations",
    "validated_trl",
    "validated_trl_reasoning",
    "validated_trl_citations",
    "components",
    "references",
    "constructive_critique",
    "proposal_url",
    "__select__",
]
# everything _except_ original_title
DISPLAY_NO_ORIG = [c for c in DISPLAY_COLS if c != "original_title"]
# full set, including original_title
DISPLAY_WITH_ORIG = DISPLAY_COLS
def _aggregate_selected() -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    # 1) historical stored
    if st.session_state.df_existing is not None:
        parts.append(_ensure_helper_cols(st.session_state.df_existing)
                     .query("__select__"))
    # 2) LLM-matched history
    for lst in st.session_state.get("hist_concepts", {}).values():
        df = _ensure_helper_cols(pd.DataFrame(lst))
        parts.append(df.query("__select__"))
    # 3) newly generated
    if st.session_state.df_to_process is not None:
        parts.append(_ensure_helper_cols(st.session_state.df_to_process)
                     .query("__select__"))
    # 4) PPT batch
    if st.session_state.df_ppt is not None:
        parts.append(_ensure_helper_cols(st.session_state.df_ppt)
                     .query("__select__"))
    if parts:
        return pd.concat(parts, ignore_index=True)
    return pd.DataFrame(columns=DISPLAY_COLS)

# Call once before rendering any tabs
st.session_state["selected_df"] = _aggregate_selected()
async def _enrich_df_async(agent_name: str, df: pd.DataFrame) -> pd.DataFrame:
    """Return *df* with any missing fields filled by *agent_name*.

    Concepts are enriched concurrently to reduce latency.
    """

    async def _enrich_one(row: pd.Series) -> dict:
        rec = row.to_dict()
        sys_p = (
            f"You are {agent_name}. Given this solution object "
            "(title + existing fields), fill ANY missing scalar fields. "
            "Return the full object as pure JSON."
        )
        return await _run_agent_async(agent_name, rec, sys_p)

    tasks = [_enrich_one(r) for _, r in df.iterrows()]
    results = await asyncio.gather(*tasks)

    for i, out in enumerate(results):
        new_row = out.get("solution")
        if not new_row and isinstance(out.get("solutions"), list) and out["solutions"]:
            new_row = out["solutions"][0]
        if not new_row:
            new_row = out

        if agent_name == "Self Critique Agent" and "suggestion" in new_row:
            new_row["constructive_critique"] = new_row.pop("suggestion")
        for k, v in new_row.items():
            if isinstance(v, (list, dict)):
                v = "\n".join(map(str, v)) if isinstance(v, list) else str(v)
            if k not in df.columns:
                df[k] = None
            if pd.isna(df.at[i, k]) or df.at[i, k] in (None, "None"):
                df.at[i, k] = v

    if "solutions" in df.columns:
        df = df.drop(columns=["solutions"])

    return df


def _enrich_df(agent_name: str, df: pd.DataFrame) -> pd.DataFrame:
    """Synchronously enrich *df* via :func:_enrich_df_async."""

    return asyncio.run(_enrich_df_async(agent_name, df))


async def _add_validated_trl_async(df: pd.DataFrame) -> pd.DataFrame:
    """
    (…full docstring describing exactly how to gather evidence, build prompts,
    call the LLM, and write back validated_trl / validated_trl_reasoning /
    validated_trl_citations—just as specified in the instructions…)
    """
    async def _validate(row: pd.Series):
        topic = row.get("description") or row.get("title")
        try:
            # 1) Gather generic evidence for this topic:
            evidence = await gather_evidence(topic)

            # 2) Format it into "[1] snippet1 (url1)\n[2] snippet2 (url2)\n…"
            evidence_block_lines = []
            for idx, ev in enumerate(evidence, start=1):
                snippet = (ev.get("snippet") or "").strip()
                snippet = sanitize_snippet(snippet)
                url = (ev.get("source_url") or "").strip()
                evidence_block_lines.append(f"[{idx}] {snippet} ({url})")
            evidence_block = "\n".join(evidence_block_lines)

            # 3) Load the TRL rubric
            rubric = load_trl_rubric()

            # 4) Grab the “TRL Assessment” schema
            trl_schema = AGENT_JSON_SCHEMAS["TRL Assessment"]

            # 5) Build system + user prompts
            system_prompt = (
                "You are an expert at assigning NASA Technology Readiness Levels (TRL). "
                "Use the following rubric to decide whether the technology is TRL 1–9:\n\n"
                f"{rubric}\n\n"
                "You will be given a concept description and a numbered evidence list. "
                "Base your TRL assignment strictly on that evidence. "
                "Return a JSON object with exactly three fields:\n"
                '  - "trl": a string between "1" and "9",\n'
                '  - "justification": a detailed explanation referencing the evidence,\n'
                '  - "citations": a list of integer indices corresponding exactly to the numbered items\n'
                "    in the evidence block that you used.\n"
            )

            user_prompt = (
                f"Concept Description:\n{topic}\n\n"
                "Evidence List (each item is [index] snippet (url)):\n"
                f"{evidence_block}\n\n"
                "Question: Based only on the evidence above, what TRL level (1–9) does this "
                "technology meet? Cite your evidence indices in the JSON output."
            )

            # 6) Pull the TRL-Assessor’s deployment details
            endpoint, deployment, version, api_key = AGENT_MODEL_MAP["TRL Assessment"]

            # 7) Call the LLM asynchronously, enforcing the schema
            trl_res = await call_llm_with_schema_async(
                endpoint=endpoint,
                deployment=deployment,
                version=version,
                role_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=trl_schema,
                max_attempts=3,
                api_key=api_key,
            )
            trl_str = trl_res.get("trl")
            just_raw = trl_res.get("justification", "").strip()
            citation_indices = trl_res.get("citations", []) or []

            # 8) Map each cited index back to its URL
            urls = []
            for idx in citation_indices:
                if isinstance(idx, int) and 1 <= idx <= len(evidence):
                    urls.append(evidence[idx - 1]["source_url"])

            # 9) Append “Citations: <url1>, <url2>” if any URLs exist
            if urls:
                combined_just = f"{just_raw}\n\nCitations: " + ", ".join(urls)
            else:
                combined_just = just_raw

            return trl_str, combined_just, urls

        except Exception as e:
            logging.warning("TRL validation failed for topic '%s': %s", topic, e)
            return None, "", []

    # 10) Run _validate() for each row in parallel
    tasks = [_validate(row) for _, row in df.iterrows()]
    results = await asyncio.gather(*tasks)

    # 11) Write back into the DataFrame
    for i, (trl_val, combined_just, urls) in enumerate(results):
        if "validated_trl" not in df.columns:
            df["validated_trl"] = None
        df.at[i, "validated_trl"] = trl_val

        if "validated_trl_reasoning" not in df.columns:
            df["validated_trl_reasoning"] = None
        df.at[i, "validated_trl_reasoning"] = combined_just

        url_str = "\n".join(urls) if urls else ""
        if "validated_trl_citations" not in df.columns:
            df["validated_trl_citations"] = None
        df.at[i, "validated_trl_citations"] = url_str

    return df

def _add_validated_trl(df: pd.DataFrame) -> pd.DataFrame:
    """Synchronously run :func:_add_validated_trl_async."""

    return asyncio.run(_add_validated_trl_async(df))


# ------------------------------------------------------------------

# ── Streamlit-compat shim ───────────────────────────────────────────────────
if not hasattr(st, "rerun"):  # Streamlit < 1.32
    st.rerun = st.rerun  # type: ignore[attr-defined]
# ─────────────────────────────────────────────────────────────────────────────
# ────────────────────────────────────────────────────────────
#  Agent ⇆ LLM convenience wrappers (three short functions)
# ────────────────────────────────────────────────────────────
from config import IDEATION_AGENTS, REVIEW_AGENTS  # NEW import
import asyncio


def _run_agent(name: str, payload: Any, role_suffix: str = "") -> dict:
    """
    Thin wrapper around AGENTS[name].act():
        • JSON-serialises *payload*
        • adds optional extra prompt *role_suffix*
    Returns the schema-validated JSON from the agent.
    """
    return AGENTS[name].act(json.dumps(payload, ensure_ascii=False), role_suffix)


async def _run_agent_async(name: str, payload: Any, role_suffix: str = "") -> dict:
    return await AGENTS[name].act(json.dumps(payload, ensure_ascii=False), role_suffix)


import re
from difflib import SequenceMatcher

async def _collect_solutions(
    problem: str,
    constraints: str,
    stream: st.delta_generator.DeltaGenerator | None = None,
    ideation_agents: list[str] | None = None,
    workflow: str | None = None,
) -> list[dict]:
    """
    Fan out to each agent, but first inject an “avoid these existing concepts” block
    so nobody re-generates what’s already in your DB.
    """
    # ── Build normalize + existing titles ────────────────────────────────
    def _normalize_title(t: str) -> str:
        return re.sub(r'[^a-z0-9]', '', t.lower())

    existing = (
        st.session_state.df_existing.to_dict("records")
        if hasattr(st.session_state, "df_existing")
        else []
    )
    existing_norms = [_normalize_title(c.get("title", "")) for c in existing]

    # ── Per-agent call ───────────────────────────────────────────────────
    async def _for_agent(agent_name: str) -> list[dict]:
        if stream:
            with stream:
                _bubble(agent_name, "Generating concepts…")
        _log("assistant", "Generating concepts…", agent_name)

        # build avoid-list so we don’t repeat existing titles
        avoid_block = ""
        if existing:
            avoid_block = (
                "### Avoid these existing concepts:\n"
                + "\n".join(f"- {c['title']}" for c in existing if c.get("title"))
            )

        # baseline role suffix
        suffix = constraints or ""
        if avoid_block:
            suffix += "\n\n" + avoid_block

        # ── Integrated Solutions Ideation overrides ───────────────────
        if workflow == "Integrated Solutions Ideation":
            if agent_name == "Product Ideation Agent":
                # ask for 15–20 novel ideas
                from asyncio import to_thread
                raw = await to_thread(
                    call_product_ideation_with_search,
                    problem,
                    existing,
                    top_k=20
                )
            elif agent_name == "Integrated Solutions Agent":
                # ask for 3–5 integrated system designs
                suffix += (
                    "\n\nPlease propose 3–5 integrated system solutions "
                    "using only Carlisle products/components to solve the problem."
                )
                raw = await _run_agent_async(agent_name, problem, suffix)
            else:
                # skip all others in this workflow
                return []
        else:
            # ── normal branch for all other workflows ───────────────────
            raw = await _run_agent_async(agent_name, problem, suffix)

        # ── unwrap dict → list[dict] if needed ───────────────────────
        if isinstance(raw, dict):
            items: list[dict] = []
            if isinstance(raw.get("solutions"), list):
                items = [s for s in raw["solutions"] if isinstance(s, dict)]
            for key in ("principles", "contradictions"):
                if isinstance(raw.get(key), list):
                    items.extend([s for s in raw[key] if isinstance(s, dict)])
            raw = items

        # ── filter & tag ─────────────────────────────────────────────
        raw = [s for s in (raw or []) if isinstance(s, dict)]
        for sol in raw:
            sol["agent"] = agent_name

        if stream:
            with stream:
                _bubble(agent_name, f"Returned {len(raw)} ideas")
        _log("assistant", f"{len(raw)} ideas", agent_name)
        return raw


    # ── Fire off all ideation agents in parallel ────────────────────────
    agents = ideation_agents or IDEATION_AGENTS
    chunks = await asyncio.gather(*[_for_agent(a) for a in agents])
    # flatten
    return [idea for chunk in chunks for idea in chunk]


import re
from difflib import SequenceMatcher
import re
from difflib import SequenceMatcher
import json

async def ideate_review_refactor(
    problem: str,
    constraints: str,
    existing_concepts: list[dict],
    stream: st.delta_generator.DeltaGenerator | None = None,
    workflow: str | None = None,
) -> tuple[list[dict], dict[str, list[str]], list[dict]]:
    """
    Returns (raw_solutions, feedback_map, refined_solutions)
    """
    # ── Helpers ──────────────────────────────────────────────────────
    def _normalize_title(t: str) -> str:
        return re.sub(r'[^a-z0-9]', '', t.lower())

    existing_norms = [
        _normalize_title(c.get("title", "")) for c in existing_concepts
    ]

    # ── PHASE-1: Ideation (always run) ─────────────────────────────────
    if stream:
        with stream:
            _bubble("System", "▶️ Phase 1 – Ideation")
    # ── 1. Collect from all agents ───────────────────────────────────
    wf = workflow or list(WORKFLOWS)[0]
    wf_agents = WORKFLOWS.get(wf, [])
    ideation_agents = [a for a in wf_agents if a in IDEATION_AGENTS]
    review_agents = [a for a in wf_agents if a in REVIEW_AGENTS]

    raw = await _collect_solutions(problem, constraints, stream, ideation_agents, workflow)
    print(f"[DEBUG] after _collect_solutions, raw has {len(raw)} items: {raw!r}")

    # ── 2. If a dict was returned with a 'solutions' key, unwrap it ───
    if isinstance(raw, dict) and "solutions" in raw:
        raw = raw["solutions"]

    # ── 3. Ensure raw is a list of dicts ────────────────────────────
    if not isinstance(raw, list):
        raw = []
    else:
        raw = [item for item in raw if isinstance(item, dict)]

    print(f"[DEBUG] after normalize, raw has {len(raw)} items: {raw!r}")
    # ── PHASE-1.1: Fuzzy-dedupe against existing titles ────────────────
    import json
    filtered: list[dict] = []
    for item in raw:
        # ensure we have a dict
        if isinstance(item, dict):
            sol = item
        elif isinstance(item, str):
            try:
                sol = json.loads(item)
            except json.JSONDecodeError:
                # skip non-JSON strings
                continue
            if not isinstance(sol, dict):
                continue
        else:
            continue

        # now safe to .get()
        title = sol.get("title", sol.get("Title", ""))
        norm = _normalize_title(title)
        # drop only if *very* similar
        if any(SequenceMatcher(None, norm, e).ratio() >= 0.75 for e in existing_norms):
            continue
        filtered.append(sol)
    raw = filtered
    print(f"[DEBUG] after dedupe (threshold .95), raw has {len(raw)} items: {raw!r}")
    # ── PHASE-1.2: Only bail out if we had existing concepts and nothing new ─
    if existing_norms and not raw:
        if stream:
            with stream:
                _bubble(
                    "System",
                    "❗ No novel concepts found—couldn’t generate any ideas beyond your existing concepts."
                )
        return [], {}, [{
            "agent": "System",
            "title": "No new concepts",
            "description": "Unable to come up with any concepts not already in your database."
        }]

    # ── PHASE-1.3: Normalize key names ─────────────────────────────────
    for sol in raw:
        if "Title" in sol and "title" not in sol:
            sol["title"] = sol.pop("Title")

    # ── PHASE-2: gather reviewer feedback ──────────────────────────────
    feedback: dict[str, list[str]] = {}
    for sol in raw:
        # try both lowercase and uppercase keys
        title = sol.get("title") or sol.get("Title")
        if not title:
            # skip any entries without a usable title
            continue
        feedback[title] = []

    async def _review(reviewer: str) -> None:
        if stream:
            with stream:
                _bubble(reviewer, "Reviewing concepts…")
        _log("assistant", "Reviewing concepts…", reviewer)
        try:
            fb = await _run_agent_async(
                reviewer, raw, "Return an array solutions:[{Title, comment}]"
            )
        except Exception:
            fb = {"solutions": []}
        for item in fb.get("solutions", []):
            t = item.get("title", "").strip()
            c = item.get("comment", "").strip()
            if t and c:
                feedback.setdefault(t, []).append(c)
        if stream:
            with stream():
                _bubble(reviewer, "Review complete")
        _log("assistant", "Review complete", reviewer)

    await asyncio.gather(*[_review(r) for r in review_agents])

    # ── PHASE-3: refine based on feedback ──────────────────────────────
    async def _refine(ideator: str) -> list[dict]:
        if stream:
            with stream():
                _bubble(ideator, "Refining their concepts…")
        _log("assistant", "Refining concepts…", ideator)
        mine = [s for s in raw if s.get("agent") == ideator]
        if not mine:
            return []
        # build title→comments list, skipping any entry without a valid title
        fb_for: list[dict] = []
        for sol in mine:
            t = sol.get("title") or sol.get("Title")
            if not t:
                continue
            fb_for.append({
                "title":   t,
                "comments": feedback.get(t, [])
            })
        role_p = (
            "You previously proposed these concepts. "
            "Improve or replace each one in light of the comments."
        )
        try:
            out = await _run_agent_async(ideator, {"concepts": mine, "feedback": fb_for}, role_p)
        except Exception:
            return []
        results = out.get("solutions", [])
        for s in results:
            s["agent"] = ideator
        if stream:
            with stream():
                _bubble(ideator, f"Returned {len(results)} refined")
        _log("assistant", f"{len(results)} refined", ideator)
        return results

    chunks = await asyncio.gather(*[_refine(i) for i in ideation_agents])
    refined = [sol for chunk in chunks for sol in chunk]

    return raw, feedback, refined




# ─────────────────────────────────────────────────────────────────────────────
# 0. Helper: inline confirm dialog (replaces st.modal)
# ─────────────────────────────────────────────────────────────────────────────
def confirm_refresh(edited: str, cascade: set[str]) -> bool:
    st.warning(
        f"🔄 **Regenerate affected sections?**\n\n"
        f"The change in **{edited}** will refresh these sections:\n"
        + "\n".join(f"- {s}" for s in cascade)
    )
    col1, col2 = st.columns(2)
    return col1.button("Proceed") and not col2.button("Cancel")


# ─────────────────────────────────────────────────────────────────────────────
# 1. Bubble & flatten helpers
# ─────────────────────────────────────────────────────────────────────────────
def _bubble(who: str, msg: str, role: str = "assistant"):
    with st.chat_message(role):
        st.markdown(f"**{who}:** {msg}")


# ------------------------------------------------------------------
#  Helper to persist conversation flow ------------------------------
def _log(role: str, text: str, who: str | None = None) -> None:
    """Append a message to the persistent conversation log."""
    st.session_state.setdefault("conversation_flow", []).append(
        {
            "role": role,
            "who": who or role.title(),
            "text": text,
        }
    )


# ---------------------------------------------------------------
# app.py  (or wherever _flatten_solution lives)
# ---------------------------------------------------------------


def _flatten_solution(agent: str, sol: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise disparate agent output → scalar columns for the table."""

    def _get(*keys) -> Any:  # helper – first non-null match
        for k in keys:
            if k in sol and sol[k] not in (None, "None", ""):
                return sol[k]

    row = {
        "agent": agent,
        "title": _get("title", "title", "Name", "name"),
        "description": None,
        "novelty_reasoning": None,
        "feasibility_reasoning": None,
        "cost_estimate": None,
        "trl": None,
        "trl_reasoning": None,
        "trl_citations": None,
        "validated_trl": None,
        "validated_trl_reasoning": None,
        "validated_trl_citations": None,
        "components": None,
        "constructive_critique": None,
    }

    # ── TRIZ Ideation Agent ────────────────────────────────────────────
    if agent.startswith("TRIZ"):
        row["description"] = _get("Architecture", "description")
        row["novelty_reasoning"] = _get("advantages")  # optional
        row["cost_estimate"] = _get("CostImpact")
        row["trl"] = _get("TRL")

    # ── Scientific Research ❶ – novelty / description ─────────────────
    elif agent == "Scientific Research Agent 1":
        row["description"] = _get("description", "Description")
        row["novelty_reasoning"] = _get("novelty_reasoning", "Novelty_reasoning")

    # ── Scientific Research ❷ – feasibility / cost / TRL ─────────────
    elif agent == "Scientific Research Agent 2":
        row["description"] = _get("description")
        row["novelty_reasoning"] = _get("novelty_reasoning")
        row["feasibility_reasoning"] = _get(
            "feasibility_reasoning", "Feasibility_reasoning"
        )
        row["cost_estimate"] = _get("cost_estimate", "Cost_estimate")
        row["trl"] = _get("trl", "TRL")
        row["trl_reasoning"] = _get("trl_reasoning", "Trl_reasoning")
        row["trl_citations"] = _get("trl_citations")

    # ── Black-Hat Thinker ─────────────────────────────────────────────
    elif agent.startswith("Black Hat"):
        pass

    # ── Self-Critique ────────────────────────────────────────────────
    elif agent.startswith("Self Critique"):
        row["constructive_critique"] = _get("comment", "Comment")

    # ── Product-Ideation ────────────────────────────────────────────────
    elif agent == "Product Ideation Agent":
        row["description"] = _get("description")
        row["novelty_reasoning"] = _get("novelty_reasoning")
        row["components"] = _get("components")
        row["references"] = _get("references")

    elif agent == "Cross-Industry Translation Agent":
        row["description"] = _get("adaptation")
        row["novelty_reasoning"] = _get("source_industry")
        row["feasibility_reasoning"] = _get("original_solution")
        row["references"] = _get("source_links")
        ch = _get("challenges")
        if isinstance(ch, list):
            row["constructive_critique"] = "\n".join(ch)

    elif agent == "Integrated Solutions Agent":
        row["description"] = _get("integration_notes")
        row["novelty_reasoning"] = _get("function")
        row["references"] = _get("sources")
    # convert lists / dicts to strings so PyArrow will accept them
    for k, v in row.items():
        if isinstance(v, (list, dict)):
            row[k] = "\n".join(map(str, v)) if isinstance(v, list) else str(v)

    return row


from typing import Dict, Any

import asyncio

from utils.llm import call_llm_with_schema_sync
from utils.trl_assessor import assess_trl_async, load_trl_rubric
from utils.evidence import gather_evidence, sanitize_snippet
from schemas import AGENT_JSON_SCHEMAS
from agents import AGENT_MODEL_MAP
import logging
logger = logging.getLogger("uvicorn.error")
def enrich_concept_card(title: str, description: str) -> Dict[str, Any]:
    """
    Return a concept card enriched by Scientific Research Agent 2 and both initial & validated TRL assessments.
    """
    # Preserve original concept essence
    card: Dict[str, Any] = {"title": title, "description": description}

    # Agent 2 enrichment
    try:
        payload = {"title": title, "description": description}
        prompt = (
            "Enrich this concept by adding structured fields (novelty_reasoning, feasibility_reasoning, cost_estimate),"
            " but do not alter or paraphrase the original title/description."
        )
        resp = _run_agent("Scientific Research Agent 2", payload, prompt)
        sols = resp.get("solutions") or []
        if sols:
            sol = _flatten_solution("Scientific Research Agent 2", sols[0])
            sol.pop("title", None)
            sol.pop("description", None)
            card.update(sol)
    except Exception as e:
        logging.warning("SciAgent2 enrichment failed: %s", e)

    # Initial TRL via async assessor (sync-run)
    try:
        result, evidence_list = asyncio.run(assess_trl_async(description))
        card["trl"] = result.get("trl")
        card["trl_reasoning"] = result.get("justification")
        citations = result.get("citations") or []
        if citations:
            urls = [evidence_list[i-1]["source_url"] for i in citations if 0 < i <= len(evidence_list)]
            card["trl_citations"] = "\n".join(urls)
    except Exception as e:
        logging.warning("Initial TRL assessor failed: %s", e)

    # Validated TRL via schema-enforced LLM
    try:
        # Gather evidence snippets synchronously
        raw_evidence = asyncio.run(gather_evidence(description))
        evidence_block = []
        for idx, ev in enumerate(raw_evidence, start=1):
            snippet = sanitize_snippet((ev.get("snippet") or "").strip())
            url = (ev.get("source_url") or "").strip()
            evidence_block.append(f"[{idx}] {snippet} ({url})")
        evidence_text = "\n".join(evidence_block)

        # Load rubric and schema
        rubric = load_trl_rubric()
        trl_schema = AGENT_JSON_SCHEMAS["TRL Assessment"]

        system_prompt = (
            "You are an expert at assigning NASA Technology Readiness Levels (TRL). "
            "Use the following rubric to decide whether the technology is TRL 1–9:\n\n"
            f"{rubric}\n\n"
            "You will be given a concept description and a numbered evidence list. "
            "Base your TRL assignment strictly on that evidence. "
            "Return a JSON object with exactly three fields:\n"
            "  - \"trl\": a string between \"1\" and \"9\",\n"
            "  - \"justification\": a detailed explanation referencing the evidence,\n"
            "  - \"citations\": a list of integer indices corresponding exactly to the numbered items in the evidence block.\n"
        )

        user_prompt = (
            f"Concept Description:\n{description}\n\n"
            f"Evidence List:\n{evidence_text}\n\n"
            "Question: Based only on the evidence above, what TRL level (1–9) does this technology meet?"
            " Cite your evidence indices in the JSON output."
        )

        endpoint, deployment, version, api_key = AGENT_MODEL_MAP["TRL Assessment"]
        val_res = call_llm_with_schema_sync(
            endpoint=endpoint,
            deployment=deployment,
            version=version,
            role_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=trl_schema,
            api_key=api_key,
        )

        card["validated_trl"] = val_res.get("trl")
        card["validated_trl_reasoning"] = val_res.get("justification", "").strip()
        val_citations = val_res.get("citations") or []
        if val_citations:
            val_urls = [raw_evidence[i-1]["source_url"] for i in val_citations if 0 < i <= len(raw_evidence)]
            card["validated_trl_citations"] = "\n".join(val_urls)
    except Exception as e:
        logging.warning("Validated TRL assessment failed: %s", e)

    return card

# ─────────────────────────────────────────────────────────────────────────────
# 2. Session defaults
# ─────────────────────────────────────────────────────────────────────────────
PE = ProposalEditor()  # global instance

_DEFAULTS = {
    "stage": "awaiting_concept",
    "chat": [],
    "current_concept": "",
    "selected_workflow": list(WORKFLOWS)[0],
    "prompt_tpl": {
        "unit": DEFAULT_COST_UNIT,
        "target_cost": DEFAULT_TARGET_COST,
        "min_trl": MIN_ACCEPTABLE_TRL,
        "constraints": "",
    },
    "solution_votes": {},
    "export_dict": {},
    "solutions_df": pd.DataFrame(),
    "conversation_flow": [],
    "current_problem": "",
    "generate": False,
    "df_to_process": None,
    # NEW — for the editor
    "_current_title":  "",
    "_previous_draft": {},
    "flash_sections": [],
    "last_diff": None,
}
for k, v in _DEFAULTS.items():
    st.session_state.setdefault(k, v)

# ── Conversation history viewer --------------------------------------------
with st.expander("💬 Conversation History", expanded=False):
    for msg in st.session_state.conversation_flow:
        with st.chat_message(msg.get("role", "assistant")):
            who = msg.get("who", msg.get("role", "assistant").title())
            st.markdown(f"**{who}:** {msg.get('text', '')}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. ↻ Regeneration logic (executes BEFORE UI is drawn)
# ─────────────────────────────────────────────────────────────────────────────
# ── 0.  ↻ Regenerate & cascade refresh  ───────────────────────────────────

regen = st.session_state.pop("_regen_payload", None)
if regen:
    concept = regen["draft"]  # draft after user edits
    edited = regen["field"]  # e.g. "performance_targets"

    # ── Build cascade set (1-hop + second-order ripple) ──────────────────
    cascade = {edited} | set(SECTION_DEPENDENCIES.get(edited, []))
    cascade |= set(
        sec for parent in list(cascade) for sec in SECTION_DEPENDENCIES.get(parent, [])
    )

    # ── Optional “ask-first” UI (falls back on ⏎ enter if st.modal missing)
    # ── Optional “ask-first” UI ───────────────────────────────────────────────
    def _confirm() -> bool:  # auto-accept
        return True

    # ── Which agent “owns” which sections?  (fine-grained routing) ───────
    # Default: Sci Research Agent 2 owns everything …
    SECTION_OWNERS = {
        sec: ["Proposal Writer Agent"] for sec in SECTION_DEPENDENCIES.keys()
    }

    # … except Risk / FMEA matters, which stay with Black-Hat Thinker
    SECTION_OWNERS["risks_mitigations"] = ["Black Hat Thinker Agent"]
    explicit_owners = set(itertools.chain.from_iterable(SECTION_OWNERS.values()))

    # ── Iterate agents & collect patches ─────────────────────────────────
    for ag_name, agent in AGENTS.items():
        # Skip if explicit routing exists and agent isn’t an owner
        if explicit_owners and ag_name not in explicit_owners:
            continue

        owned = [sec for sec in cascade if sec in agent.schema["properties"]]
        if not owned:
            continue  # nothing for this agent to update

        role_p = (
            f"You are {ag_name}. The user modified {edited}.\n"
            f"Update these sections to stay consistent: {', '.join(owned)}.\n"
            "Return one JSON object containing **only** those keys."
        )
        user_p = json.dumps(
            {
                "current_draft": concept,
                "previous_draft": st.session_state.get("_previous_draft", {}),
                "section_changed": edited,
            },
            ensure_ascii=False,
        )

        try:
            raw_patch = agent.act(user_p, role_p)  # schema-validated
            # 1) Never change the title
            raw_patch.pop("title", None)
            # 2) Only apply the keys you explicitly cascaded
            valid_patch = {k: v for k, v in raw_patch.items() if k in cascade}
            concept.update(valid_patch)
            st.session_state["_previous_draft"] = json.loads(json.dumps(concept))
            st.rerun()
        except Exception as e:
            st.warning(f"{ag_name} failed: {e}")

    # ── Sticky-note diff & visual flash list ─────────────────────────────
    diff = deepdiff.DeepDiff(
        st.session_state.get("_previous_draft", {}),
        concept,
        ignore_order=True,
        view="tree",
    )
    if diff:
        st.session_state["last_diff"] = diff.to_json(indent=2)

    flashed = set(st.session_state.get("flash_sections", []))
    flashed.update(cascade)
    st.session_state["flash_sections"] = list(flashed)

    st.session_state["last_diff"] = diff.to_json(indent=2) if diff else None

    st.session_state["_previous_draft"] = json.loads(json.dumps(concept))
    st.rerun()
# ───────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 4. Sidebar – prompt template, problem, export
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    tab_inputs, tab_export, tab_enrich = st.tabs([
        "Inputs",
        "Export",
        "Enrich",
    ])


    with tab_inputs:
        st.subheader("📝 New Problem Statement")
        prob = st.text_area("Problem statement …")
        st.subheader("⚙️ Prompt Template")
        tpl = st.session_state.prompt_tpl
        # allow pasting in your desired outcomes for this ideation run
        tpl["outcomes"] = st.text_area(
            "Desired outcomes (e.g. performance targets, user benefits…)",
            value=tpl.get("outcomes", ""),
            help="Describe what you want the generated concepts to achieve."
        )
        tpl["min_trl"] = st.slider(
            "Minimum acceptable TRL",
            1, 9,
            value=tpl["min_trl"],
            help="Filter out concepts below this Technology Readiness Level."
        )
        tpl["constraints"] = st.text_area(
            "Extra constraints (optional)",
            value=tpl.get("constraints", ""),
            help="Any additional requirements or boundaries for the concepts."
        )
        if st.button("Submit", key="submit_main") and prob.strip():
            # STEP 1: Fetch semantically similar concepts
            sim_results = get_similar_concepts(prob)
            rows: list[dict] = []
            for item in sim_results:
                sim = item.get("similarity", 0)
                for c in item.get("concepts", []):
                    c["similarity"] = sim
                    rows.append(c)
            df = pd.DataFrame(rows)
            if not df.empty:
                df = df.sort_values("similarity", ascending=False)
            st.session_state.df_existing = df
            st.session_state.current_problem = prob
            st.session_state.df_to_process = None
        # 1) Kick off the LLM match
        if st.button("🔍 Find Similar Problems (Search Historical)") and prob.strip():
            st.session_state.similar = get_similar_problems_via_llm(prob, top_k=5)
            st.session_state.pop("hist_problems", None)
            st.session_state.pop("hist_concepts", None)

        # 2) Show the matches (or a message if none)
        if st.session_state.get("similar"):
            sim_df = (
                pd.DataFrame(st.session_state.similar)
                  .sort_values("score", ascending=False)
                  .rename(columns={
                      "problem_statement": "Problem Statement",
                      "score":             "Relevance"
                  })
            )
            st.subheader("⚡ Similar Existing Problems")
            st.dataframe(sim_df, use_container_width=True)

            # 3) Multi-select which problems to load
            choices = st.multiselect(
                "Load concepts for…",
                sim_df["Problem Statement"].tolist(),
                key="hist_problems"
            )

            # 4) Fetch & stash all selected
            if st.button("📥 Load Concepts (from Selected Problem Statements)"):
                st.session_state.hist_concepts = {
                    p: get_concepts_for(p) for p in choices
                }

        elif st.session_state.get("tried_similar"):
            st.info("No semantically similar problems found.")

        


        # STEP 2: Always ask whether to generate more
        if st.session_state.get("df_existing") is not None:
            gen_choice = st.radio("Generate more concepts?", ("No", "Yes"))
            st.session_state.generate = (gen_choice == "Yes")

        # STEP 3: If user wants to generate, show workflow selector + start button
        if st.session_state.get("generate"):
            choice = st.selectbox("Choose ideation workflow", list(WORKFLOWS.keys()))
            st.session_state.selected_workflow = choice
            if st.button("Start Ideation", key="start_ideation_sidebar"):
                # build the combined prompt from desired outcomes, TRL, and extra constraints
                tpl = st.session_state.prompt_tpl
                parts = []
                if tpl.get("outcomes"):
                    parts.append(f"Desired Outcomes:\n{tpl['outcomes']}")
                parts.append(f"TRL ≥ {tpl['min_trl']}")
                if tpl.get("constraints"):
                    parts.append(f"Constraints:\n{tpl['constraints']}")
                full_prompt = "\n\n".join(parts)

                # RUN the full ideate→review→refine→enrich→TRL pipeline
                raw, feedback_map, refined = asyncio.run(
                    ideate_review_refactor(
                        st.session_state.current_problem,
                        full_prompt,
                        st.session_state.df_existing.to_dict("records"),
                        workflow=choice,
                    )
                )
                rows = [_flatten_solution(sol["agent"], sol) for sol in refined]
                df = pd.DataFrame(rows)
                df = _ensure_helper_cols(df)
                # --- ENRICHMENT & TRL VALIDATION ---
                df = _enrich_df("Scientific Research Agent 2", df)
                df = _enrich_df("Self Critique Agent", df)
                df = _add_validated_trl(df)
                st.session_state.df_to_process = _ensure_helper_cols(df)

                from io import BytesIO
                from utils.proposal_editor import ProposalEditor

                # 1) stash your newly generated/enriched concepts
                st.session_state.df_to_process = _ensure_helper_cols(df)
                records = (
                st.session_state.df_to_process
                    .where(pd.notnull, None)
                    .to_dict("records")
                )

                # 2) clear out any old drafts so you don’t carry over your card JSON
                st.session_state.pop(ProposalEditor._SSKEY, None)
                st.session_state.pop("_current_title", None)

                # 3) fire off the build_docx_report, saving *only* the Proposal-Writer narratives
                #buf = BytesIO()
                #build_docx_report(records, buf, on_each_narrative=PE.save)

                # 4) promote into review stage
                #df_sol = st.session_state.df_to_process.copy()
                #df_sol["original_title"] = df_sol["title"]
                #st.session_state.solutions_df = df_sol
                #st.session_state.refined_concepts = records
                #st.session_state.stage            = "chat"

                # 5) rerun so the “Review & Chat” tab lights up
                st.rerun()

    with tab_export:
        sel = st.session_state.selected_df
        st.header("📦 Selected Concepts")
        st.dataframe(sel[DISPLAY_NO_ORIG], use_container_width=True)

        if sel.empty:
            st.info("No concepts selected.")
        else:
            if st.button("Export Concept Cards as PPTX"):
                buf = BytesIO()
                workflow = st.session_state.get("selected_workflow", "default")
                build_pptx_from_df(sel, buf, workflow=workflow)
                buf.seek(0)
                st.download_button("Download PPTX", buf,
                    "concept_cards_selected.pptx",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )

            if st.button("Build Detailed Proposal (DOCX)"):
                buf = BytesIO()
                build_docx_report(sel.where(pd.notnull, None).to_dict("records"), buf,
                                on_each_narrative=PE.save)
                buf.seek(0)
                st.download_button("Download Proposal", buf,
                    f"proposal_{int(time.time())}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
        # ───────────────────────────────────────────────────────────────
        # 📄 Download Any Drafts in the ProposalEditor
        # ───────────────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("📄 Download Proposal Drafts")

        # Grab all the drafts that have been saved into PE by build_docx_report(..., on_each_narrative=PE.save)
        drafts = PE._drafts()  # returns a dict: title -> draft_object

        if not drafts:
            st.info("No drafts available yet.  Run a proposal build or chat first.")
        else:
            for title, draft in drafts.items():
                # serialize a single-concept DOCX
                buf = BytesIO()
                build_docx_report([draft], buf)
                buf.seek(0)
                # download button per draft
                safe_name = title.replace(" ", "_").replace("/", "_")
                st.download_button(
                    label=f"Download Proposal: {title}",
                    data=buf,
                    file_name=f"{safe_name}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )



    with tab_enrich:
        st.header("➕ Enrich Concept(s)")

        # File upload: PPTX for multiple slides or JSON for one concept
        upload = st.file_uploader(
            "Upload PPTX (multiple slides) or JSON (one concept)",
            type=["pptx", "json"],
            key="enrich_uploader"
        )

        # If PPTX is uploaded, ask for its associated problem statement
        ppt_problem = ""
        if upload and upload.name.lower().endswith(".pptx"):
            ppt_problem = st.text_area(
                "Associated problem statement",
                value=st.session_state.get("current_problem", ""),
                key="ppt_problem"
            )

        # Manual entry fallback
        st.markdown("**Or manually enter a concept**")
        manual_problem = st.text_area(
            "Problem statement",
            value=st.session_state.get("current_problem", ""),
            key="manual_problem"
        )
        manual_title = st.text_input(
            "Concept title",
            key="manual_title"
        )
        manual_desc = st.text_area(
            "Concept description",
            key="manual_desc",
            height=150
        )

        # Enrich button
        if st.button("Enrich", key="enrich_concepts_btn"):
            enriched_cards: list[dict[str, Any]] = []

            # Determine which problem statement to use
            problem_stmt = ppt_problem or manual_problem or st.session_state.get("current_problem", "")

            # 1) Uploaded PPTX: batch enrich each slide
            if upload is not None and upload.name.lower().endswith(".pptx"):
                try:
                    cards = read_concept_cards(upload)
                    upload.seek(0)
                except Exception as e:
                    st.error(f"Failed to parse PPTX: {e}")
                    cards = []
                for card in cards:
                    title = card.get("title", "").strip()
                    desc = card.get("description", "").strip()
                    if not (title and desc):
                        st.warning(f"Skipping slide without title/description: {card}")
                        continue
                    try:
                        enriched = enrich_concept_card(title, desc)
                    except Exception as e:
                        st.warning(f"Enrichment failed for '{title}': {e}")
                        continue
                    merged = {**card, **enriched}
                    merged["original_title"] = title
                    merged["title"] = title
                    merged["problem_statement"] = problem_stmt
                    enriched_cards.append(merged)

            # 2) Uploaded JSON: single concept
            elif upload is not None and upload.name.lower().endswith(".json"):
                try:
                    card = json.load(upload)
                    upload.seek(0)
                except Exception as e:
                    st.error(f"Failed to parse JSON: {e}")
                    card = {}
                title = card.get("title", "").strip()
                desc = card.get("description", "").strip()
                if title and desc:
                    try:
                        enriched = enrich_concept_card(title, desc)
                    except Exception as e:
                        st.error(f"Enrichment failed: {e}")
                        enriched = {}
                    merged = {**card, **enriched}
                    merged["original_title"] = title
                    merged["title"] = title
                    merged["problem_statement"] = problem_stmt
                    enriched_cards.append(merged)
                else:
                    st.warning("JSON must include 'title' and 'description'.")

            # 3) No upload: manual single concept
            else:
                title = manual_title.strip()
                desc = manual_desc.strip()
                if not (title and desc):
                    st.warning("Please enter both a title and description for manual enrichment.")
                else:
                    try:
                        enriched = enrich_concept_card(title, desc)
                    except Exception as e:
                        st.error(f"Enrichment failed: {e}")
                        enriched = {}
                    merged = {"title": title, "description": desc, **enriched}
                    merged["original_title"] = title
                    merged["problem_statement"] = problem_stmt
                    enriched_cards.append(merged)

            # 4) Append to session and optionally commit
            if enriched_cards:
                # ── Persist as a PPT‐only DataFrame ──────────────────────────
                df_ppt = _ensure_helper_cols(pd.DataFrame(enriched_cards))
                # make sure we use original_title as the displayed title
                df_ppt["title"] = df_ppt["original_title"]
                st.session_state.df_ppt = df_ppt

                st.success(f"✅ Parsed and enriched {len(enriched_cards)} slide concepts—see “Newly Generated” tab.")
                # don’t change stage, so the UI will stay on “Newly Generated” next render
                st.rerun()
            else:
                st.info("No concepts were enriched.")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Main Canvas – split into three tabs
# ─────────────────────────────────────────────────────────────────────────────


if (
    st.session_state.get("df_existing") is not None
    or st.session_state.get("df_to_process") is not None
    or st.session_state.get("hist_concepts")
):
    # Let user toggle Table vs. Cards
    view_mode = st.radio("🔄 Display as", ("Table", "Cards"), horizontal=True, key="view_mode")

    # Define the three main tabs
    tab_hist, tab_new, tab_review = st.tabs([
        "💾 Historical Concepts",
        "💡 Newly Generated",
        "📝 Review & Chat"
    ])
    
    # ── Tab 1: Historical Concepts ────────────────────────────────────────
    with tab_hist:
        # 1) Render concepts fetched on “Submit”
        if st.session_state.get("df_existing") is not None:
            st.subheader(f"🔍 Stored Concepts for: {st.session_state.current_problem}")
            df_existing = _ensure_helper_cols(st.session_state.df_existing)

            # ── Select All Historical Concepts ─────────────────────────────
            select_all_hist = st.checkbox(
                "Select All Historical Concepts",
                value=df_existing["__select__"].all(),
                key="select_all_hist"
            )
            if select_all_hist:
                df_existing["__select__"] = True
            elif "select_all_hist" in st.session_state and not select_all_hist:
                df_existing["__select__"] = False

            # write back before rendering
            st.session_state.df_existing = df_existing
            if view_mode == "Table":
                edited = st.data_editor(
                    df_existing[DISPLAY_NO_ORIG],
                    use_container_width=True,
                    column_config={
                        "__select__": st.column_config.CheckboxColumn("Select"),
                        "trl":       st.column_config.ProgressColumn("TRL", min_value=1, max_value=9),
                        "proposal_url": st.column_config.LinkColumn("Proposal"),
                    },
                    disabled=["agent", "title", "description"],
                    key="table_existing_editor"
                )
                # write back checkbox changes
                for idx in edited.index:
                    st.session_state.df_existing.at[idx, "__select__"] = edited.at[idx, "__select__"]
            else:
                render_concept_cards(df_existing, select_key_prefix="existing")

        # 2) Render concepts fetched by “Find Similar Problems”
        if st.session_state.get("hist_concepts"):
            st.markdown("---")
            st.subheader("⚡ LLM-Matched Historical Concepts")
            for i, (problem, concept_list) in enumerate(st.session_state.hist_concepts.items()):
                st.markdown(f"**Problem:** {problem}")
                hist_df = _ensure_helper_cols(pd.DataFrame(concept_list))
                # ── Select All for this Historical‐Problem Group ───────────────
                select_all_group = st.checkbox(
                    f"Select All “{problem}” Concepts",
                    value=hist_df["__select__"].all(),
                    key=f"select_all_hist_{i}"
                )
                if select_all_group:
                    hist_df["__select__"] = True
                elif f"select_all_hist_{i}" in st.session_state and not select_all_group:
                    hist_df["__select__"] = False

                # write back before rendering
                st.session_state.hist_concepts[problem] = hist_df.to_dict("records")
                if view_mode == "Table":
                    edited = st.data_editor(
                        hist_df[DISPLAY_NO_ORIG],
                        use_container_width=True,
                        column_config={"__select__": st.column_config.CheckboxColumn("Select")},
                        disabled=["agent", "title", "description"],
                        key=f"hist_{i}_editor"
                    )
                    st.session_state.hist_concepts[problem] = edited.to_dict("records")
                else:
                    render_concept_cards(hist_df, select_key_prefix=f"hist_{i}")

        # 3) Aggregate both stored + historical selections
        combined = []

        # a) Stored
        if st.session_state.get("df_existing") is not None:
            df_ex = _ensure_helper_cols(st.session_state.df_existing)
            combined.extend(df_ex[df_ex["__select__"]].to_dict("records"))

        # b) Historical
        for records in st.session_state.get("hist_concepts", {}).values():
            combined.extend([rec for rec in records if rec.get("__select__", False)])

        if combined:
            st.subheader("📋 Selected Historical Concepts to Enrich")
            df_sel = _ensure_helper_cols(pd.DataFrame(combined))
            st.dataframe(df_sel[DISPLAY_NO_ORIG], use_container_width=True)
            # ── NEW: allow direct PPTX export of the selected historical concepts ──
            if st.button("📤 Export Selected Concept Cards (PPTX)", key="export_hist_sel"):
                buf = BytesIO()
                build_pptx_from_df(df_sel, buf)      # reuse your existing helper
                buf.seek(0)
                st.download_button(
                    "Download Selected Concept Cards",
                    buf,
                    file_name="concept_cards_selected.pptx",
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "presentationml.presentation"
                    )
                )

        if st.button("Enrich & Queue for Export", key="enrich_hist_all"):
            enriched_cards = []
            for r in combined:
                # run the enrichment
                card = enrich_concept_card(r["title"], r["description"])
                # stash the original title
                card["title"] = r["title"]
                card["original_title"] = r["title"]
                enriched_cards.append(card)

            # build a DataFrame — _ensure_helper_cols will fill in missing DISPLAY_COLS
            df_en = _ensure_helper_cols(pd.DataFrame(enriched_cards))
            df_en["title"] = df_en["original_title"]

            # now df_en has both:
            #   - original_title = the pre-enrich r["title"]
            #   - title          = whatever the agent filled in
            st.session_state.solutions_df = pd.concat(
                [st.session_state.get("solutions_df", pd.DataFrame()), df_en],
                ignore_index=True
            )

            st.session_state.refined_concepts = df_en.to_dict("records")
            from io import BytesIO

            # seed the ProposalEditor drafts
            buf = BytesIO()
            build_docx_report(
                st.session_state.refined_concepts,
                buf,
                on_each_narrative=PE.save
            )
            st.session_state.stage = "chat"
            # 1) set a flag
            st.session_state.show_export_hint = True
            st.toast("✅ Historical concepts enriched and queued")
            st.rerun()
        if st.session_state.get("show_export_hint"):
            st.info(
                "✅ Historical concepts are queued for export.  \n"
                "Now switch to **Export → Generate Detailed Proposal** to build your DOCX.")
    # clear it so it only shows once
    del st.session_state["show_export_hint"]

    # ── Tab 2: Newly Generated & Enriched ───────────────────────────────────
    # ── Tab 2: Newly Generated & Enriched ───────────────────────────────────
    with tab_new:
        if st.session_state.get("df_to_process") is not None:
            st.subheader("💡 Newly Generated & Enriched Concepts")
            df_new = _ensure_helper_cols(st.session_state.df_to_process)
            wf     = st.session_state.selected_workflow
            # ── Select All Newly Generated Concepts ─────────────────────────
            select_all_new = st.checkbox(
                "Select All Newly Generated Concepts",
                value=df_new["__select__"].all(),
                key="select_all_new"
            )
            if select_all_new:
                df_new["__select__"] = True
            elif "select_all_new" in st.session_state and not select_all_new:
                df_new["__select__"] = False

            # write back before rendering
            st.session_state.df_to_process = df_new
            # --- pick your columns based on workflow ---
            if wf == "Cross-Industry Ideation":
                # copy the flattened values
                df_new["original_solution"] = df_new["feasibility_reasoning"]
                df_new["challenges"]          = df_new["constructive_critique"]
                df_new["source_links"]        = df_new["references"]

                # rename for display
                df_new = df_new.rename(columns={
                    "novelty_reasoning": "Industry",
                    "original_solution": "Original Solution",
                    "challenges":        "Adaptation Challenges",
                    "source_links":      "Source URLs",
                })
                custom_cols = ["agent","title","description","Industry",
                    "Original Solution","Adaptation Challenges","Source URLs",
                    # and still show the rest...
                    "novelty_reasoning","feasibility_reasoning","cost_estimate",
                    "trl","trl_reasoning","trl_citations",
                    "validated_trl","validated_trl_reasoning","validated_trl_citations",
                    "components","references","constructive_critique",
                ]

            elif wf == "Integrated Solutions Ideation":
                # use same columns as your TRIZ workflow
                custom_cols = ["agent","title","description",
                    "novelty_reasoning","feasibility_reasoning","cost_estimate",
                    "trl","trl_reasoning","trl_citations",
                    "validated_trl","validated_trl_reasoning","validated_trl_citations",
                    "components","references","constructive_critique",
                ]

            else:
                # default for Product-Ideation, TRIZ, etc.
                custom_cols = ["agent","title","description",
                    "novelty_reasoning","feasibility_reasoning","cost_estimate",
                    "trl","trl_reasoning","trl_citations",
                    "validated_trl","validated_trl_reasoning","validated_trl_citations",
                    "components","references","constructive_critique",
                ]

            # always let the user select rows
            display_cols = ["__select__"] + custom_cols
            # only keep the ones that exist right now
            display_cols = [c for c in display_cols if c in df_new.columns]
            display_df = df_new[display_cols]

            if view_mode == "Table":
                edited = st.data_editor(
                    display_df,
                    use_container_width=True,
                    column_config={
                        "__select__":       st.column_config.CheckboxColumn("Select"),
                        "trl":               st.column_config.ProgressColumn(
                                                "TRL", min_value=1, max_value=9, format="%d"
                                            ),
                        "validated_trl":     st.column_config.ProgressColumn(
                                                "Validated TRL", min_value=1, max_value=9, format="%d"
                                            ),
                    },
                    disabled=["agent","title"],
                    key="table_new_editor"
                )
                # write back the checkbox state
                for idx in edited.index:
                    st.session_state.df_to_process.at[idx, "__select__"] = edited.at[idx, "__select__"]
            else:
                render_concept_cards(df_new, select_key_prefix="new")


            # 1) Commit to storage
            if st.button("Commit these concepts to storage", key="commit_storage"):
                records = df_new.assign(
                    problem_statement=st.session_state.current_problem
                ).where(pd.notnull(df_new), None).to_dict("records")
                success, status, body = save_concepts(
                    st.session_state.current_problem, records
                )
                if success:
                    # parse the response (assuming your API returns a JSON list of objects with "id")
                    saved = json.loads(body)
                    # write back the new IDs into your solutions_df
                    for rec, info in zip(records, saved):
                        # find the row by title (or another unique key)
                        mask = df_new["title"] == rec["title"]
                        df_new.loc[mask, "id"] = info.get("id")
                    st.success(f"✅ Saved {len(records)} concepts (with IDs).")
                    st.session_state.solutions_df = df_new
                    st.session_state.refined_concepts = df_new.to_dict("records")
                    st.session_state.stage = "chat"
                    st.session_state.show_export_hint = True
                    st.toast("✅ Concepts committed and queued for export")
                    st.rerun()
                else:
                    st.error(f"❌ Save failed (status={status}).")

            # 2) Enrich & Queue for Export (like historical tab)
            if st.button("Enrich & Queue for Export (New)", key="enrich_new_all"):
                # 1. reload the latest selections
                df_current = _ensure_helper_cols(st.session_state.df_to_process)
                selected = df_current[df_current["__select__"]]

                if selected.empty:
                    st.warning("⚠️ No concepts selected to enrich.")
                else:
                    # 2. only enrich the ones the user actually picked
                    enriched_cards = []
                    for r in selected.to_dict("records"):
                        card = enrich_concept_card(r["title"], r["description"])
                        card["original_title"] = r["title"]
                        card["title"] = r["title"]
                        enriched_cards.append(card)

                    # 3. stack them onto your export queue
                    df_en = _ensure_helper_cols(pd.DataFrame(enriched_cards))
                    # carry over the title into original_title
                    df_en["original_title"] = df_en["title"]
                    st.session_state.solutions_df = pd.concat(
                        [st.session_state.get("solutions_df", pd.DataFrame()), df_en],
                        ignore_index=True
                    )
                    
                    st.session_state.refined_concepts = df_en.to_dict("records")
                    from io import BytesIO

                    # seed the ProposalEditor drafts
                    buf = BytesIO()
                    build_docx_report(
                        st.session_state.refined_concepts,
                        buf,
                        on_each_narrative=PE.save
                    )
                    st.session_state.stage = "chat"
                    st.session_state.show_export_hint = True
                    st.toast("✅ New concepts enriched and queued")
                    st.rerun()
            # export hint (once only)
            if st.session_state.get("show_export_hint"):
                st.info(
                    "✅ Concepts are queued for export.  \n"
                    "Switch to **Export → Generate Detailed Proposal** to build your DOCX."
                )
                # only show once
                del st.session_state["show_export_hint"]

        # ────────── New PPT section ──────────
        if st.session_state.df_ppt is not None:
            st.markdown("---")
            st.subheader("📥 Additional Concepts from PPT")

            df_ppt = st.session_state.df_ppt
            # Select All
            select_all_ppt = st.checkbox(
                "Select All PPT Concepts",
                value=df_ppt["__select__"].all(),
                key="select_all_ppt"
            )
            if select_all_ppt:
                df_ppt["__select__"] = True
            elif "select_all_ppt" in st.session_state and not select_all_ppt:
                df_ppt["__select__"] = False
            st.session_state.df_ppt = df_ppt

            # Render table or cards
            if view_mode == "Table":
                # only pull __select__ once, and drop it from DISPLAY_COLS
                ppt_cols = ["__select__"] + [
                    c for c in DISPLAY_COLS
                    if c not in ("original_title", "__select__")
                ]
                edited = st.data_editor(
                    df_ppt[ppt_cols],
                    use_container_width=True,
                    column_config={
                        "__select__": st.column_config.CheckboxColumn("Select"),
                        "trl":       st.column_config.ProgressColumn("TRL", min_value=1, max_value=9,format="%d"),
                        "validated_trl":       st.column_config.ProgressColumn("Validated TRL", min_value=1, max_value=9,format="%d")
                    },
                    disabled=["agent","title"],
                    key="ppt_table_editor"
                )
                for idx in edited.index:
                    st.session_state.df_ppt.at[idx, "__select__"] = edited.at[idx, "__select__"]
            else:
                render_concept_cards(df_ppt, select_key_prefix="ppt")

            # Commit only PPT concepts
            if st.button("Commit PPT Concepts to storage", key="commit_ppt"):
                selected = df_ppt[df_ppt["__select__"]]
                if selected.empty:
                    st.warning("⚠️ No PPT concepts selected.")
                else:
                    records = (
                        selected
                        .assign(problem_statement=st.session_state.current_problem)
                        .where(pd.notnull, None)
                        .to_dict("records")
                    )
                    ok, status, body = save_concepts(
                        st.session_state.current_problem, records
                    )
                    if ok:
                        saved = json.loads(body)
                        # write back IDs
                        for rec, info in zip(records, saved):
                            mask = df_ppt["original_title"] == rec["original_title"]
                            df_ppt.loc[mask, "id"] = info.get("id")
                        st.success(f"✅ Saved {len(records)} PPT concept(s).")
                        # now merge into your solutions_df so they flow through export
                        merged = pd.concat([st.session_state.solutions_df, df_ppt], ignore_index=True)
                        st.session_state.solutions_df = merged
                        st.session_state.refined_concepts = merged.where(pd.notnull, None).to_dict("records")
                        st.session_state.stage = "chat"
                        st.session_state.show_export_hint = True
                        st.toast("✅ PPT concepts queued for proposal export")
                        st.rerun()
                    else:
                        st.error(f"❌ Save failed (status={status}).")


    # ── Tab 3: Review & Chat ───────────────────────────────────────────────
    from io import BytesIO

    with tab_review:
        st.subheader("📋 Final Selection")

        # 1) Grab the master “selected concepts” DataFrame
        sel = st.session_state.get("selected_df", pd.DataFrame()).copy()

        # 2) If nothing at all is selected upstream
        if sel.empty:
            st.info("No concepts selected. Go back to the other tabs and pick some.")
        else:
            # 3) One last “Select All / Deselect All” control
            all_sel = bool(sel["__select__"].all())
            new_all = st.checkbox("Select All / Deselect All", value=all_sel, key="final_select_all")
            if new_all != all_sel:
                sel["__select__"] = new_all

            # 4) Render editable table so users can un-check individual rows if they wish
            edited = st.data_editor(
                sel[DISPLAY_WITH_ORIG],
                column_config={
                    "__select__":     st.column_config.CheckboxColumn("Keep"),
                    "trl":            st.column_config.ProgressColumn("TRL", min_value=1, max_value=9),
                    "validated_trl":  st.column_config.ProgressColumn("Validated TRL", min_value=1, max_value=9),
                },
                use_container_width=True,
                key="final_editor",
            )
            # write edits back into session
            sel.loc[edited.index, DISPLAY_COLS] = edited
            st.session_state.selected_df = sel

            # 5) Filter down to exactly the ones to export / propose
            final = sel.query("__select__")

            st.markdown(f"**{len(final)} concept(s) selected for export/proposal**")

            # ───────────────────────────────────────────────────────────────
            # 📝 Build single DOCX covering *all* selected concepts
            # ───────────────────────────────────────────────────────────────
            if final.empty:
                st.warning("Select at least one concept to build the proposal.")
            else:
                if st.button("📝 Build Detailed Proposal DOCX", key="build_final_docx"):
                    buf = BytesIO()
                    build_docx_report(
                        final.where(pd.notnull, None).to_dict("records"),
                        buf,
                        on_each_narrative=PE.save
                    )
                    buf.seek(0)
                    st.download_button(
                        "📥 Download Detailed Proposal",
                        buf,
                        file_name=f"proposal_{int(time.time())}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

            # ───────────────────────────────────────────────────────────────
            # 📄 Proposal Draft Preview & Editor
            # ───────────────────────────────────────────────────────────────
            titles = list(PE._drafts())
            if titles:
                current = st.session_state.get("_current_title", titles[0])
                if current not in titles:
                    current = titles[0]
                sel_title = st.selectbox("📄 Proposal Draft Preview", titles, index=titles.index(current))
                st.session_state["_current_title"] = sel_title

                col_preview, col_editor = st.columns((5, 3), gap="large")
                with col_preview:
                    PE.preview(build_docx_report)
                with col_editor:
                    PE.render()

            # ───────────────────────────────────────────────────────────────
            # 💬 Concept-level Chat
            # ───────────────────────────────────────────────────────────────
            st.markdown("### 💬 Concept Chat")
            chat_choices = sel["title"].tolist()
            chat_choice = st.selectbox("Select concept to chat about:", chat_choices, key="chat_select")
            if st.button("Open Chat", key="open_final_chat"):
                st.session_state.active_chat_concept = chat_choice

            if active := st.session_state.get("active_chat_concept"):
                rec     = sel.query("title==@active").iloc[0].to_dict()
                history = st.session_state.setdefault(f"_chat_{active}", [])
                with st.expander(f"Chat – {active}", expanded=True):
                    for msg in history:
                        with st.chat_message(msg["role"]):
                            st.markdown(msg["text"])
                    if user_msg := st.chat_input("Your turn…", key=f"chat_input_{active}"):
                        # 1) record the user’s question
                        history.append({"role": "user", "text": user_msg})
                        _log("user", user_msg, "User")

                        # 2) grab the full proposal draft for this concept
                        drafts = PE._drafts()
                        full_draft = drafts.get(active, {})

                        # 3) directly invoke the LLM for Scientific Research Agent 2
                        import json
                        from utils.llm import call_llm

                        endpoint, deployment, version, api_key = AGENT_MODEL_MAP["Scientific Research Agent 2"]
                        system_prompt = (
                            "You are Scientific Research Agent 2.\n\n"
                            "Here is the full proposal draft (all sections):\n\n"
                            f"{json.dumps(full_draft, indent=2)}\n\n"
                            "Please answer the following question as concisely and accurately as possible:"
                        )
                        user_prompt = user_msg

                        resp = call_llm(
                            endpoint=endpoint,
                            deployment=deployment,
                            version=version,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt
                        )

                        # 4) extract the answer text
                        if isinstance(resp, str):
                            answer = resp
                        else:
                            answer = resp.get("text", resp.get("analysis", str(resp)))

                        # 5) record and display the assistant’s answer
                        history.append({"role": "assistant", "text": answer})
                        _log("assistant", answer, "Scientific Research Agent 2")
                        st.rerun()
            st.markdown("---")
            if st.button("➕ Spawn Refined Concept from Conversation", key="spawn_refined"):
                # 1) collect draft + history
                drafts  = PE._drafts()
                full    = drafts.get(active, {})
                history = st.session_state.setdefault(f"_chat_{active}", [])

                # 2) call the agent
                import json
                from utils.llm import call_llm
                ep, dep, ver, key = AGENT_MODEL_MAP["Scientific Research Agent 2"]
                sys_p = (
                    "You are Scientific Research Agent 2.  You've seen this proposal draft and the follow-up Q&A:\n\n"
                    f"Draft:\n{json.dumps(full, indent=2)}\n\n"
                    "Conversation:\n"
                    + "\n".join(f"{m['role']}: {m['text']}" for m in history)
                    + "\n\nNow produce a single new, fully-formed concept (with title, description, novelty_reasoning, "
                      "feasibility_reasoning, cost_estimate, trl, etc.) in JSON."
                )
                user_p = "Please output one JSON object with all of the above fields."

                resp = call_llm(
                    endpoint=ep,
                    deployment=dep,
                    version=ver,
                    system_prompt=sys_p,
                    user_prompt=user_p
                )

                # 3) normalize to a dict
                if isinstance(resp, str):
                    try:
                        parsed = json.loads(resp)
                    except json.JSONDecodeError:
                        st.error("❌ Could not parse agent response as JSON.")
                        st.stop()
                    sol_obj = parsed
                elif isinstance(resp, dict):
                    sol_obj = resp
                else:
                    st.error("❌ Unexpected response format from agent.")
                    st.stop()

                # 4) extract the first solution if it’s wrapped in a list
                if "solutions" in sol_obj and isinstance(sol_obj["solutions"], list) and sol_obj["solutions"]:
                    new_raw = sol_obj["solutions"][0]
                elif "solution" in sol_obj and isinstance(sol_obj["solution"], dict):
                    new_raw = sol_obj["solution"]
                else:
                    new_raw = sol_obj

                # 5) flatten and append
                new_row = _flatten_solution("Scientific Research Agent 2", new_raw)
                new_row["__select__"] = True
                new_row["id"] = None

                df = st.session_state.solutions_df.copy()
                st.session_state.solutions_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

                # re-build selected_df so it shows up immediately
                st.session_state.selected_df = _aggregate_selected()

                # 6) seed ProposalEditor with its narrative
                from io import BytesIO
                buf = BytesIO()
                build_docx_report([new_row], buf, on_each_narrative=PE.save)

                # switch preview/editor
                st.session_state["_current_title"]   = new_row["title"]
                st.session_state.active_chat_concept = new_row["title"]
                st.toast("✅ Spawned new concept and loaded its draft")
                st.rerun()
            # ───────────────────────────────────────────────────────────────
            # 📌 Commit to Blob Storage
            # ───────────────────────────────────────────────────────────────
            st.markdown("### 📌 Commit Proposals to Blob Storage")
            if st.button("📦 Commit Selected Proposals", key="commit_final"):
                to_commit = final.copy()
                if to_commit.empty:
                    st.warning("Select at least one concept before committing.")
                else:
                    successes = 0
                    for idx, rec in to_commit.iterrows():
                        # 1) Ensure it’s saved in your API
                        cid = rec.get("id")
                        if cid is None:
                            single = [rec.where(pd.notnull, None).to_dict()]
                            ok, status, body = save_concepts(st.session_state.current_problem, single)
                            if not ok:
                                st.error(f"❌ Failed to save “{rec['title']}” (status={status})")
                                continue
                            cid = json.loads(body)[0].get("id")
                            st.session_state.selected_df.at[idx, "id"] = cid

                        # 2) Generate a one-concept DOCX
                        buf = BytesIO()
                        build_docx_report([rec.to_dict()], buf)
                        buf.seek(0)

                        # 3) Upload it
                        files = {
                            "file": (
                                f"{rec['title']}.docx",
                                buf.getvalue(),
                                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                        }
                        resp = requests.post(
                            f"{API_BASE_URL}/concepts/{cid}/proposal",
                            files=files
                        )
                        if resp.ok:
                            url = resp.json().get("proposal_url", "")
                            st.session_state.selected_df.at[idx, "proposal_url"] = url
                            successes += 1
                        else:
                            st.error(f"❌ Upload failed for “{rec['title']}”: {resp.status_code}")

                    if successes:
                        st.success(f"✅ Committed {successes} proposal(s) to storage.")
                    else:
                        st.warning("No proposals were successfully committed.")
# ─── 3) Fixed footer ───────────────────────────────────────────────────
st.markdown(
    """
    <style>
      .app-footer {
        position: fixed;
        bottom: 0; left: 0; right: 0;
        background-color: #F2F2F2;
        text-align: center;
        padding: 8px 0;
        font-size: 0.8rem;
        color: #666;
      }
    </style>
    <div class="app-footer">
      Powered by Carlisle Research & Innovation • © 2025 Carlisle Construction Materials
    </div>
    """,
    unsafe_allow_html=True,
)
