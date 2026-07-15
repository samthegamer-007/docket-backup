"""
generation.py
Stage 3 of the pipeline - LLM call via Groq.
Receives ONLY the retrieved statutes/case law + timeline stage info -
NEVER the user's original raw story. Explains content in plain language,
strictly informational, never advisory.
"""

import os
import json
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

GENERATION_SYSTEM_PROMPT = """You are a legal information explainer. You will be given:
- Retrieved statute text
- Retrieved case law summaries
- The current procedural stage and its legal basis

Your job is to explain this content in plain, simple language for someone with no legal background.

STRICT RULES:
- Write in THIRD PERSON only. Describe what the law says and what the procedure is.
- NEVER use second-person advice language: no "you should", "I recommend", "in your case", "your best option", "I suggest".
- NEVER assess whether someone has a strong or weak case.
- NEVER tell the reader what to do next - only describe what the law/process provides.
- If asked to produce a document template, generate a GENERIC template ("a notice of this type typically includes...") not a personalized letter.

Respond ONLY with valid JSON in this shape:
{
  "statute_explanations": [ {"id": "<id>", "plain_language": "<explanation>"} ],
  "case_law_explanations": [ {"id": "<id>", "plain_language": "<explanation>"} ],
  "stage_explanation": "<plain language explanation of the current procedural stage and its legal basis>"
}
"""


def generate_explanation(retrieved_content: dict, stage_info: dict) -> dict:
    """
    Calls Groq to generate plain-language explanations grounded ONLY in
    retrieved content and stage info - never the user's raw story.
    """
    user_content = json.dumps({
        "statutes": retrieved_content.get("statutes", []),
        "case_law": retrieved_content.get("case_law", []),
        "stage": {
            "label": stage_info.get("current_stage_label"),
            "legal_basis": stage_info.get("legal_basis"),
            "description": stage_info.get("description"),
        },
    })

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
    )

    raw_output = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        raise ValueError(f"Generation did not return valid JSON: {raw_output}")

    return parsed


NEWS_GENERATION_SYSTEM_PROMPT = """You are a legal information explainer. You will be given
a list of recent news articles related to a legal topic.

STRICT RULES:
- Write in THIRD PERSON only. Summarize what each article reports.
- NEVER use second-person advice language: no "you should", "I recommend", "in your case".
- NEVER speculate on how a development might affect the reader's personal situation.
- NEVER predict outcomes ("this means you will win/lose").
- Just factually summarize what each article says, plainly.

Respond ONLY with valid JSON in this shape:
{
  "news_explanations": [ {"id": "<id>", "plain_language": "<factual summary>"} ]
}
"""


def generate_news_explanation(news_articles: list) -> dict:
    """
    Explains retrieved news articles in plain, factual language.
    Same safety rules as generate_explanation - no advice, no prediction.
    """
    if not news_articles:
        return {"news_explanations": []}

    user_content = json.dumps({"articles": news_articles})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": NEWS_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
    )

    raw_output = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        raise ValueError(f"News generation did not return valid JSON: {raw_output}")

    return parsed
