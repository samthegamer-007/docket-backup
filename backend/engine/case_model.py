"""
case_model.py
Handles all reads/writes to the `cases` table in Supabase.
This is a thin data-access layer - no business logic here, that lives in state_machine.py.
"""

import os
from datetime import date
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def create_case(case_type: str, first_stage_id: str, facts: dict) -> dict:
    """
    Creates a new case row and returns it.
    """
    payload = {
        "case_type": case_type,
        "current_stage": first_stage_id,
        "stage_start_date": date.today().isoformat(),
        "facts": facts,
        "history": [
            {"stage": first_stage_id, "entered": date.today().isoformat()}
        ],
    }
    result = supabase.table("cases").insert(payload).execute()
    return result.data[0]


def get_case(case_id: str) -> dict | None:
    """
    Fetches a single case by id. Returns None if not found.
    """
    result = supabase.table("cases").select("*").eq("id", case_id).execute()
    if not result.data:
        return None
    return result.data[0]


def update_case_stage(case_id: str, new_stage_id: str) -> dict:
    """
    Advances a case to a new stage, appending to history and resetting stage_start_date.
    """
    case = get_case(case_id)
    if case is None:
        raise ValueError(f"Case {case_id} not found")

    new_history = case["history"] + [
        {"stage": new_stage_id, "entered": date.today().isoformat()}
    ]

    payload = {
        "current_stage": new_stage_id,
        "stage_start_date": date.today().isoformat(),
        "history": new_history,
    }
    result = supabase.table("cases").update(payload).eq("id", case_id).execute()
    return result.data[0]


def update_case_facts(case_id: str, new_facts: dict) -> dict:
    """
    Merges new facts into the existing facts blob (e.g. user adds info mid-conversation).
    """
    case = get_case(case_id)
    if case is None:
        raise ValueError(f"Case {case_id} not found")

    merged_facts = {**case["facts"], **new_facts}
    result = (
        supabase.table("cases")
        .update({"facts": merged_facts})
        .eq("id", case_id)
        .execute()
    )
    return result.data[0]
