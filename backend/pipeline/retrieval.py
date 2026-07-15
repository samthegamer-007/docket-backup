"""
retrieval.py
Stage 2 of the pipeline - plain code, NOT an AI call.
Looks up relevant statute text and case summaries from the curated corpus.
Falls back to Tavily search only when the local corpus doesn't have enough
for a given case type - this keeps the primary path fast, free, and predictable.
"""

import os
import json
import re
from tavily import TavilyClient

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "..", "corpus")

with open(os.path.join(CORPUS_DIR, "statutes.json"), "r") as f:
    STATUTES = json.load(f)

with open(os.path.join(CORPUS_DIR, "cases.json"), "r") as f:
    CURATED_CASES = json.load(f)

tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

MIN_CASES_BEFORE_FALLBACK = 2  # if local corpus has fewer than this, supplement with Tavily


def retrieve_statutes(case_type: str) -> list:
    """
    Returns curated statute chunks for a case type from the local corpus.
    """
    return STATUTES.get(case_type, [])


def retrieve_curated_case_law(case_type: str) -> list:
    """
    Returns manually curated, human-verified case law for a case type.
    This is the primary, reliable path - checked before ever calling Tavily.
    """
    return CURATED_CASES.get(case_type, [])


def _clean_id_from_url(url: str) -> str:
    """
    Builds a clean, safe node id from a URL, stripping slashes and other
    characters that break downstream id usage. Falls back to a hash-like
    trim if the URL doesn't contain a usable numeric doc id.
    """
    match = re.search(r"(\d{5,})", url)
    if match:
        return f"case_{match.group(1)}"
    # Fallback: strip non-alphanumeric characters entirely
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", url)
    return f"case_{cleaned[-12:]}" if cleaned else "case_unknown"


def retrieve_supplementary_case_law(case_type: str, query_hint: str = "") -> list:
    """
    Uses Tavily to pull in additional case law when the curated corpus
    is thin. Only called as a fallback - keep this rare so search costs and
    unpredictability stay low, and results stay more reliable.
    """
    query = f"Indian case law {case_type.replace('_', ' ')} {query_hint}".strip()

    try:
        results = tavily_client.search(
            query=query,
            search_depth="basic",
            max_results=3,
            include_domains=["indiankanoon.org"],
        )
    except Exception:
        # Fail gracefully - retrieval should never crash the whole pipeline
        return []

    cases = []
    for r in results.get("results", []):
        url = r.get("url", "")
        cases.append({
            "id": _clean_id_from_url(url),
            "title": r.get("title", "Untitled case"),
            "text": r.get("content", "")[:500],  # cap length fed into generation
            "source_url": url,
        })
    return cases


def retrieve_for_case(case_type: str) -> dict:
    """
    Main entry point for Stage 2. Uses curated statutes and curated case law
    as the primary, reliable source. Only supplements with Tavily search if
    the curated case law corpus doesn't have enough entries for this case type.
    """
    statutes = retrieve_statutes(case_type)
    curated_cases = retrieve_curated_case_law(case_type)

    if len(curated_cases) >= MIN_CASES_BEFORE_FALLBACK:
        case_law = curated_cases
    else:
        supplementary = retrieve_supplementary_case_law(case_type)
        case_law = curated_cases + supplementary

    return {
        "statutes": statutes,
        "case_law": case_law,
    }
