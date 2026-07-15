"""
extraction.py
Stage 1 of the pipeline - LLM call via Groq.
Takes the user's messy free-text story and pulls out ONLY the case type
and minimal neutral facts. The original narrative never travels past this stage.
"""

import os
import json
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SUPPORTED_CASE_TYPES = ["rental_deposit"]  # extend as you add verticals

EXTRACTION_SYSTEM_PROMPT = """You are a legal topic classifier. Your ONLY job is to extract:
1. The case_type from this fixed list: {case_types}
2. Minimal neutral facts needed for procedural tracking: amount (if mentioned), any dates mentioned, and the other party's role (e.g. "landlord", "seller").

You must NOT include any personal narrative, emotional language, or opinions in your output.
You must NOT try to answer the user's question or give any advice.
Respond ONLY with valid JSON in this exact shape, nothing else:

{{
  "case_type": "<one of the supported types, or null if none match>",
  "key_facts": {{
    "amount": <number or null>,
    "date_mentioned": "<ISO date string or null>",
    "other_party_role": "<string or null>"
  }}
}}
"""


def extract_case_details(user_story: str) -> dict:
    """
    Calls Groq to extract structured case_type + key_facts from raw user text.
    Returns a validated dict. Raises ValueError if the model output isn't valid JSON
    or case_type isn't supported.
    """
    system_prompt = EXTRACTION_SYSTEM_PROMPT.format(case_types=SUPPORTED_CASE_TYPES)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_story},
        ],
        temperature=0,
    )

    raw_output = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        raise ValueError(f"Extraction did not return valid JSON: {raw_output}")

    case_type = parsed.get("case_type")
    if case_type not in SUPPORTED_CASE_TYPES:
        raise ValueError(f"Unsupported or missing case_type: {case_type}")

    return parsed
