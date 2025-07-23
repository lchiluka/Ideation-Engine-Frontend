# ---------------------------------------------------------------------------
# schemas.py – complete JSON schemas (FULL DETAIL)
# ---------------------------------------------------------------------------
from __future__ import annotations

"""Centralised JSON Schemas for all agents + proposal writer.

You can import `SCHEMA_PW` and `AGENT_JSON_SCHEMAS` anywhere in the project,
then validate with `jsonschema.validate()` or use the pre‑built
`PROPOSAL_VALIDATOR` object.
"""

# ===========================================================================
# 1. Exhaustive Proposal‑Writer schema  (SCHEMA_PW)
# ===========================================================================

SCHEMA_PW: dict = {
    "type": "object",
    "required": [
        "title", "executive_summary", "problem_statement", "concept_overview",
        "technical_details", "performance_targets", "manufacturing_process",
        "cost_feasibility", "risks_mitigations", "sustainability",
        "applications", "experimental_design", "validation_plan", "kpi_table",
        "ip_landscape", "references",
    ],
    "properties": {
        "title":              {"type": "string"},
        "executive_summary":  {"type": "string"},
        "problem_statement":  {"type": "string"},
        "concept_overview":   {"type": "string"},

        "technical_details": {
            "type": "object",
            "required": ["materials", "structure"],
            "properties": {
                "materials":    {"type": "array", "items": {"type": "string"}},
                "structure":    {"type": "string"},
                "formulation":  {"type": "array", "items": {"type": "string"}},
                "design_rules": {"type": "array", "items": {"type": "string"}},
            },
        },

        "performance_targets": {"type": "object", "additionalProperties": {"type": "string"}},

        "manufacturing_process": {
            "type": "object",
            "required": ["route"],
            "properties": {
                "route":           {"type": "string"},
                "critical_params": {"type": "object", "additionalProperties": {"type": "string"}},
                "scale_readiness": {"type": "string"},
            },
        },

        "cost_feasibility": {
            "type": "object",
            "required": ["trl"],
            "properties": {
                "cost_breakdown": {"type": "string"},
                "capex_estimate": {"type": "string"},
                "trl":            {"type": "integer", "minimum": 1, "maximum": 9},
                "trl_rationale":  {"type": "string"},
            },
        },

        "risks_mitigations": {"type": "array", "items": {"type": "string"}},
        "sustainability":    {"type": "string"},
        "applications":      {"type": "array", "items": {"type": "string"}},
        "experimental_design":         {"type": "array", "items": {"type": "string"}},

        "validation_plan": {
            "type": "object",
            "properties": {
                "mechanical":    {"type": "array", "items": {"type": "string"}},
                "thermal":       {"type": "array", "items": {"type": "string"}},
                "chemical":      {"type": "array", "items": {"type": "string"}},
                "environmental": {"type": "array", "items": {"type": "string"}},
            },
        },

        "kpi_table":    {"type": "object", "additionalProperties": {"type": "string"}},
        "ip_landscape": {"type": "string"},
        "references":   {"type": "array", "items": {"type": "string"}},
    },
}

# ===========================================================================
# 2. Agent‑specific output schemas  (AGENT_JSON_SCHEMAS)
# ===========================================================================

AGENT_JSON_SCHEMAS: dict[str, dict] = {
    # ---------------------------------------------------------------------
    # TRIZ Ideation Agent
    # ---------------------------------------------------------------------
    "TRIZ Ideation Agent": {
        "type": "object",
        "properties": {
            "contradictions": {
                "type": "object",
                "properties": {
                    "technical": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "improving_parameter": {"type": "string"},
                                "worsening_parameter": {"type": "string"},
                                "description":         {"type": "string"},
                            },
                            "required": ["improving_parameter", "worsening_parameter", "description"],
                        },
                    },
                    "physical": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "parameter_1": {"type": "string"},
                                "state_1":     {"type": "string"},
                                "parameter_2": {"type": "string"},
                                "state_2":     {"type": "string"},
                                "description": {"type": "string"},
                            },
                            "required": ["parameter_1", "state_1", "parameter_2", "state_2", "description"],
                        },
                    },
                },
                "required": ["technical", "physical"],
            },
            "principles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "number": {"type": "integer"},
                        "name":   {"type": "string"},
                    },
                    "required": ["number", "name"],
                },
            },
            "solutions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title":                   {"type": "string"},
                        "description":             {"oneOf": [{ "type": "string"     },{ "type": "array", "items": { "type": "string" } }]},
                        "triz_principles_applied": {"type": "array",  "items": {"type": "integer"}},
                        "advantages":              {"type": "array",  "items": {"type": "string"}},
                        "challenges":              {"type": "array",  "items": {"type": "string"}},
                    },
                    "required": ["title", "description", "triz_principles_applied", "advantages", "challenges"],
                },
            },
        },
        "required": ["contradictions", "principles", "solutions"],
    },

    # ---------------------------------------------------------------------
    # Scientific Research Agent 1
    # ---------------------------------------------------------------------
    "Scientific Research Agent 1": {
        "type": "object",
        "properties": {
            "solutions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title":            {"type": "string"},
                        "description":      {"type": "string"},
                        "novelty_reasoning":{"type": "string"},
                        "applications":     {"type": "array", "items": {"type": "string"}},
                        "sources":          {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["title", "description", "novelty_reasoning", "applications", "sources"],
                },
            },
        },
        "required": ["solutions"],
    },

    # ---------------------------------------------------------------------
    # Scientific Research Agent 2
    # ---------------------------------------------------------------------
    "Scientific Research Agent 2": {
        "type": "object",
        "properties": {
            "solutions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title":               {"type": "string"},
                        "feasibility_reasoning":{"type": "string"},
                        "cost_estimate":       {"type": "string"},
                        "trl":                 {"type": "integer"},
                        "trl_reasoning":       {"type": "string"},
                    },
                    "required": ["title", "feasibility_reasoning", "cost_estimate", "trl", "trl_reasoning"],
                },
            },
        },
        "required": ["solutions"],
    },

    # ---------------------------------------------------------------------
    # Product Ideation Agent (SCAMPER)
    # ---------------------------------------------------------------------
    "Product Ideation Agent": {
        "type": "object",
        "properties": {
            "solutions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title":             { "type": "string" },
                        "description":       { "type": "string" },
                        "scamper_steps":     {
                            "type": "array",
                            "items": { "type": "string" }
                        },
                        "components":        {
                            "type": "array",
                            "items": { "type": "string" }
                        },
                        "novelty_reasoning": { "type": "string" },
                        "references": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": { "type": "string" },
                                    "url":   { "type": "string", "format": "uri" }
                                },
                                "required": ["url"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": [
                        "title",
                        "description",
                        "scamper_steps",
                        "components"
                    ],
                    "additionalProperties": False
                }
            }
        },
        "required": ["solutions"],
        "additionalProperties": False
    },

    # ---------------------------------------------------------------------
    # Cross‑Industry Translation Agent
    # ---------------------------------------------------------------------
    "Cross-Industry Translation Agent": {
        "type": "object",
        "properties": {
            "solutions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title":            {"type": "string"},
                        "source_industry":  {"type": "string"},
                        "source_problem":   {"type": "string"},
                        "original_solution": {"type": "string"},
                        "adaptation":       {"type": "string"},
                        "challenges":       {"type": "array", "items": {"type": "string"}},
                        "source_links":     {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "title",
                        "source_industry",
                        "source_problem",
                        "original_solution",
                        "adaptation",
                        "challenges",
                        "source_links"
                    ],
                },
            },
        },
        "required": ["solutions"],
    },

    # ---------------------------------------------------------------------
    # Integrated Solutions Agent
    # ---------------------------------------------------------------------
    "Integrated Solutions Agent": {
        "type": "object",
        "properties": {
            "control_strategies": {"type": "string"},
            "metrics":            {"type": "array", "items": {"type": "string"}},
            "sources":            {"type": "array", "items": {"type": "string"}},
            "solutions":          {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "title":             {"type": "string"},
                    "function":          {"type": "string"},
                    "integration_notes": {"type": "string"},
                },
                "required": ["title", "function", "integration_notes"],
            }},
        },
        "required": ["control_strategies", "metrics", "sources", "solutions"],
    },

    # ---------------------------------------------------------------------
    # Black Hat Thinker Agent
    # ---------------------------------------------------------------------
    "Black Hat Thinker Agent": {
        "type": "object",
        "properties": {
            "solutions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title":        {"type": "string"},
                        "severity":     {"type": "integer"},
                        "probability":  {"type": "integer"},
                        "detectability":{"type": "integer"},
                        "mitigation":   {"type": "string"},
                        "risk_notes":   {"type": "string"},
                    },
                    "required": [
                        "title", "severity", "probability", "detectability", "mitigation", "risk_notes"
                    ],
                },
            },
        },
        "required": ["solutions"],
    },

    # ---------------------------------------------------------------------
    # Self‑Critique Agent
    # ---------------------------------------------------------------------
    "Self Critique Agent": {
        "type": "object",
        "properties": {
            "solutions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title":      {"type": "string"},
                        "comment": {"type": "string"},
                    },
                    "required": ["title", "comment"],
                },
            },
        },
        "required": ["solutions"],
        "additionalProperties": False
    },
}

# Append schemas for Literature Review & Proposal Writer --------------------
# schemas.py  – replace the old rule
# ── schemas.py ──  Literature Review Agent
AGENT_JSON_SCHEMAS["Literature Review Agent"] = {
    "type": "object",
    "properties": {
        "citations": {
            "type": "array",
            "items": {
                "oneOf": [
                    {"type": "string"},
                    {
                        "type": "object",
                        "required": ["title", "journal", "year"],
                        "properties": {
                            "title":  {"type": "string"},
                            "journal":{"type": "string"},
                            "year":   {"type": ["integer", "string"]},
                            "PMID":   {"type": "string"},
                            "Patent#":{"type": "string"},
                            "PMID/Patent#": {"type": "string"}      # ← NEW
                        },
                        "additionalProperties": False
                    }
                ]
            }
        }
    },
    "required": ["citations"]
}


AGENT_JSON_SCHEMAS["Proposal Writer Agent"] = SCHEMA_PW
# ── add two optional string fields ───────────────
AGENT_JSON_SCHEMAS["Scientific Research Agent 2"]["properties"].update({
    "description":        {"type": "string"},
    "novelty_reasoning":  {"type": "string"},
    "trl_citations": {"type": "array", "items": {"type": "string"}},
})
# ── TRL Assessment schema ─────────────────────────────
AGENT_JSON_SCHEMAS["TRL Assessment"] = {
    "type": "object",
    "properties": {
        "trl": {"type": "string"},
        "justification": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["trl", "justification", "citations"],
}

#  runs won’t break, but SR-2 is free to include them.)

# ===========================================================================
# 3. Validator helper
# ===========================================================================
from jsonschema import Draft7Validator
PROPOSAL_VALIDATOR = Draft7Validator(SCHEMA_PW)

# End of file
