"""
retrieval.py
Stage 2 of the pipeline - plain code, NOT an AI call.
Looks up relevant statute text and case summaries from the curated corpus.
Falls back to Tavily search only when the local corpus doesn't have enough
for a given case type - this keeps the primary path fast, free, and predictable.
"""

import os
import json
from tavily import TavilyClient

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "..", "corpus")

with open(os.path.join(CORPUS_DIR, "statutes.json"), "r") as f:
    STATUTES = json.load(f)

tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

MIN_STATUTES_BEFORE_FALLBACK = 1  # if local corpus has fewer than this, supplement with Tavily


def retrieve_statutes(case_type: str) -> list:
    """
    Returns curated statute chunks for a case type from the local corpus.
    """
    return STATUTES.get(case_type, [])


def retrieve_supplementary_case_law(case_type: str, query_hint: str = "") -> list:
    """
    Uses Tavily to pull in recent/additional case law when the curated corpus
    is thin. Only called as a fallback - keep this rare so search costs and
    unpredictability stay low.
    """
    query = f"Indian case law {case_type.replace('_', ' ')} {query_hint}".strip()

    try:
        results = tavily_client.search(
            query=query,
            search_depth="basic",
            max_results=3,
            include_domains=["indiankanoon.org"],
        )
    except Exception as e:
        # Fail gracefully - retrieval should never crash the whole pipeline
        return []

    cases = []
    for r in results.get("results", []):
        cases.append({
            "id": r.get("url", "")[-12:],  # simple id from url tail
            "title": r.get("title", "Untitled case"),
            "text": r.get("content", "")[:500],  # cap length fed into generation
            "source_url": r.get("url", ""),
        })
    return cases


def retrieve_for_case(case_type: str) -> dict:
    """
    Main entry point for Stage 2. Combines local statutes with case law,
    supplementing via Tavily only if the local corpus is thin.
    """
    statutes = retrieve_statutes(case_type)

    # For now, local corpus only has statutes - case law always comes via Tavily fallback.
    # Once you curate cases.json properly, check that first before falling back.
    case_law = retrieve_supplementary_case_law(case_type)

    return {
        "statutes": statutes,
        "case_law": case_law,
    }
