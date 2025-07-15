# utils/query_generator.py

from utils.llm import call_llm
import os

# Load Azure OpenAI credentials
AZURE_OPENAI_ENDPOINT    = "https://harsh-m6qoycs6-eastus2.cognitiveservices.azure.com"
AZURE_OPENAI_DEPLOYMENT  = "gpt-4o"
AZURE_OPENAI_API_VERSION = "2025-01-01-preview"
AZURE_OPENAI_API_KEY     = "DjlhGHwAzeElpQGkUTYRSlZ1s7R3mlxyviIUQODK8kGcxzmrmiryJQQJ99BBACHYHv6XJ3w3AAAAACOGIyMt"

def generate_academic_search_query(concept_description: str, max_keywords: int = 8) -> str:
    '''
    Use the LLM to turn a long concept_description into a short, keyword-dense
    query for arXiv/CrossRef. The output should be ≤ max_keywords words.
    '''
    system_prompt = f"""
You are an expert at crafting concise, high-precision academic search queries.
Given a paragraph describing an R&D concept, extract and return the top {max_keywords} keywords
(i.e. nouns, verbs, technical terms) as a short phrase for searching arXiv/CrossRef.
Avoid generic stopwords, units, and numbers. Output should be a single line of text,
ideally ≤ {max_keywords} words, separated by spaces.
""".strip()

    user_prompt = f"""Concept description:

{concept_description}
"""

    raw_response = call_llm(
        AZURE_OPENAI_ENDPOINT,
        AZURE_OPENAI_DEPLOYMENT,
        AZURE_OPENAI_API_VERSION,
        system_prompt,
        user_prompt,
        api_key=AZURE_OPENAI_API_KEY
    )

    cleaned = raw_response.strip().strip('"').strip("'")
    # If the LLM returned an error code (e.g. "Error 401: Unauthorized"), force fallback:
    if cleaned.lower().startswith("error "):
        raise RuntimeError(f"LLM query generation failed: {cleaned}")
    return cleaned
