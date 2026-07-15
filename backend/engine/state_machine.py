"""
state_machine.py
Pure logic for the procedural timeline. No AI, no database calls here -
this is the "real system" that works whether or not the LLM layer exists.
"""

import json
import os
from datetime import date, datetime

TIMELINE_MAP_PATH = os.path.join(
    os.path.dirname(__file__), "..", "corpus", "timeline_map.json"
)

with open(TIMELINE_MAP_PATH, "r") as f:
    TIMELINE_MAP = json.load(f)


def get_stage_definition(case_type: str, stage_id: str) -> dict:
    """
    Looks up a single stage's definition (window, next stage, legal basis) for a case type.
    """
    stages = TIMELINE_MAP.get(case_type, {}).get("stages", [])
    for stage in stages:
        if stage["id"] == stage_id:
            return stage
    raise ValueError(f"Stage '{stage_id}' not found for case type '{case_type}'")


def get_first_stage(case_type: str) -> dict:
    """
    Returns the first stage definition for a given case type - used when a new case is created.
    """
    stages = TIMELINE_MAP.get(case_type, {}).get("stages", [])
    if not stages:
        raise ValueError(f"No stages defined for case type '{case_type}'")
    return stages[0]


def compute_progress(case_type: str, current_stage_id: str, stage_start_date: str) -> dict:
    """
    Pure math: given a case's current stage and when it started, compute
    days elapsed, days remaining, and whether it's eligible to advance.
    No AI, no advice - just the deterministic timeline calculation.
    """
    stage_def = get_stage_definition(case_type, current_stage_id)
    all_stages = TIMELINE_MAP[case_type]["stages"]

    start = datetime.fromisoformat(stage_start_date).date()
    today = date.today()
    days_elapsed = (today - start).days

    window_days = stage_def["window_days"]
    days_remaining = max(window_days - days_elapsed, 0)
    eligible_to_advance = days_elapsed >= window_days

    return {
        "current_stage_id": current_stage_id,
        "current_stage_label": stage_def["label"],
        "current_stage_order": stage_def["order"],
        "total_stages": len(all_stages),
        "days_elapsed": days_elapsed,
        "window_days": window_days,
        "days_remaining": days_remaining,
        "eligible_to_advance": eligible_to_advance,
        "next_stage_id": stage_def.get("next_stage"),
        "legal_basis": stage_def["legal_basis"],
        "description": stage_def["description"],
    }


def get_all_stage_labels(case_type: str) -> list:
    """
    Returns an ordered list of all stage labels for a case type - used to
    render the progress area's full stepper (e.g. "Stage 2 of 4").
    """
    stages = TIMELINE_MAP.get(case_type, {}).get("stages", [])
    return [{"id": s["id"], "label": s["label"], "order": s["order"]} for s in stages]
