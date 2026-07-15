"""
output_filter.py
Stage 4 of the pipeline - plain code, NOT an AI call.
Final safety net: scans generated text for advisory language before it
reaches the user. This is the last line of defense, not the only one -
the prompt in generation.py already forbids this language, but models
drift, so this catches what slips through.
"""

import re

BANNED_PHRASES = [
    r"\byou should\b",
    r"\byou must\b",
    r"\byou need to\b",
    r"\bi recommend\b",
    r"\bi suggest\b",
    r"\bin your case\b",
    r"\byour best option\b",
    r"\byour best bet\b",
    r"\bmy advice\b",
    r"\byou have a strong case\b",
    r"\byou have a weak case\b",
    r"\byou will win\b",
    r"\byou will lose\b",
]

FALLBACK_MESSAGE = (
    "This platform provides general legal information only. "
    "For guidance specific to your situation, please consult a qualified lawyer."
)


def contains_advisory_language(text: str) -> bool:
    """
    Checks a single string against the banned phrase list, case-insensitive.
    """
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in BANNED_PHRASES)


def filter_generation_output(generated: dict) -> dict:
    """
    Walks through every text field in the generation output. If any field
    contains advisory language, that specific field is replaced with the
    fallback message rather than blocking the entire response - this keeps
    the rest of the (safe) explanation usable.
    """
    filtered = {"statute_explanations": [], "case_law_explanations": []}

    for item in generated.get("statute_explanations", []):
        text = item.get("plain_language", "")
        if contains_advisory_language(text):
            item["plain_language"] = FALLBACK_MESSAGE
            item["flagged"] = True
        filtered["statute_explanations"].append(item)

    for item in generated.get("case_law_explanations", []):
        text = item.get("plain_language", "")
        if contains_advisory_language(text):
            item["plain_language"] = FALLBACK_MESSAGE
            item["flagged"] = True
        filtered["case_law_explanations"].append(item)

    stage_text = generated.get("stage_explanation", "")
    if contains_advisory_language(stage_text):
        filtered["stage_explanation"] = FALLBACK_MESSAGE
        filtered["stage_flagged"] = True
    else:
        filtered["stage_explanation"] = stage_text

    return filtered
