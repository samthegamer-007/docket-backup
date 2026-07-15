"""
routes.py
The API surface the frontend calls. Wires together all four pipeline
stages plus the state machine engine.
"""

from flask import Blueprint, request, jsonify

from pipeline.extraction import extract_case_details
from pipeline.retrieval import retrieve_for_case
from pipeline.generation import generate_explanation, generate_news_explanation
from pipeline.output_filter import filter_generation_output, contains_advisory_language, FALLBACK_MESSAGE
from pipeline.news_retrieval import retrieve_news
from engine import state_machine
from engine import case_model

api = Blueprint("api", __name__)


def build_graph_payload(case_type: str, retrieved: dict, explanations: dict, progress: dict) -> dict:
    """
    Assembles the node/edge graph structure the frontend's Obsidian-style
    visual area renders, plus the progress payload for the progress area.
    """
    nodes = []
    edges = []

    # Statute nodes
    for i, statute in enumerate(retrieved.get("statutes", [])):
        node_id = statute["id"]
        explanation = next(
            (e["plain_language"] for e in explanations.get("statute_explanations", [])
             if e["id"] == node_id),
            statute.get("text", "")
        )
        nodes.append({
            "id": node_id,
            "label": statute["title"],
            "type": "statute",
            "detail": explanation,
        })

    # Case law nodes
    for case in retrieved.get("case_law", []):
        node_id = case["id"]
        explanation = next(
            (e["plain_language"] for e in explanations.get("case_law_explanations", [])
             if e["id"] == node_id),
            case.get("text", "")
        )
        nodes.append({
            "id": node_id,
            "label": case["title"],
            "type": "case",
            "detail": explanation,
            "source_url": case.get("source_url"),
        })
        # Connect case law to the first statute node as "interprets" (simple heuristic for v1)
        if nodes and any(n["type"] == "statute" for n in nodes):
            first_statute_id = next(n["id"] for n in nodes if n["type"] == "statute")
            edges.append({"from": first_statute_id, "to": node_id, "relation": "interprets"})

    # Timeline stage nodes - one per stage in the case type's process
    all_stages = state_machine.get_all_stage_labels(case_type)
    for i, stage in enumerate(all_stages):
        node_id = f"stage_{stage['id']}"
        is_current = stage["id"] == progress["current_stage_id"]
        nodes.append({
            "id": node_id,
            "label": stage["label"],
            "type": "timeline_stage",
            "is_current": is_current,
            "order": stage["order"],
        })
        if i > 0:
            prev_node_id = f"stage_{all_stages[i - 1]['id']}"
            edges.append({"from": prev_node_id, "to": node_id, "relation": "next_stage"})

    return {"nodes": nodes, "edges": edges}


@api.route("/analyze", methods=["POST"])
def analyze():
    """
    Entry point when a user first describes their situation.
    Runs the full 4-stage pipeline and creates a new case.
    """
    body = request.get_json(force=True)
    user_story = body.get("user_story", "").strip()

    if not user_story:
        return jsonify({"error": "user_story is required"}), 400

    # Stage 1: Extraction
    try:
        extracted = extract_case_details(user_story)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422

    case_type = extracted["case_type"]
    key_facts = extracted["key_facts"]

    # Create the case in Supabase, starting at the first stage
    first_stage = state_machine.get_first_stage(case_type)
    case = case_model.create_case(case_type, first_stage["id"], key_facts)

    # Stage 2: Retrieval
    retrieved = retrieve_for_case(case_type)

    # Compute current progress (pure math, no AI)
    progress = state_machine.compute_progress(
        case_type, case["current_stage"], case["stage_start_date"]
    )

    # Stage 3: Generation
    try:
        generated = generate_explanation(retrieved, progress)
    except ValueError as e:
        return jsonify({"error": f"Generation failed: {str(e)}"}), 502

    # Stage 4: Output filter
    safe_explanations = filter_generation_output(generated)

    graph = build_graph_payload(case_type, retrieved, safe_explanations, progress)

    return jsonify({
        "case_id": case["id"],
        "case_type": case_type,
        "nodes": graph["nodes"],
        "edges": graph["edges"],
        "timeline": progress,
    })


@api.route("/case/<case_id>", methods=["GET"])
def get_case(case_id):
    """
    Retrieves an existing case's current state - used when the user reopens
    a case in the app.
    """
    case = case_model.get_case(case_id)
    if case is None:
        return jsonify({"error": "Case not found"}), 404

    progress = state_machine.compute_progress(
        case["case_type"], case["current_stage"], case["stage_start_date"]
    )

    retrieved = retrieve_for_case(case["case_type"])

    try:
        generated = generate_explanation(retrieved, progress)
        safe_explanations = filter_generation_output(generated)
    except ValueError:
        safe_explanations = {"statute_explanations": [], "case_law_explanations": [], "stage_explanation": ""}

    graph = build_graph_payload(case["case_type"], retrieved, safe_explanations, progress)

    return jsonify({
        "case_id": case["id"],
        "case_type": case["case_type"],
        "nodes": graph["nodes"],
        "edges": graph["edges"],
        "timeline": progress,
        "facts": case["facts"],
    })


@api.route("/case/<case_id>/advance", methods=["POST"])
def advance_case(case_id):
    """
    Advances a case to its next stage. Only succeeds if the current stage's
    window has actually elapsed - this is enforced by the state machine,
    not left to user or AI discretion.
    """
    case = case_model.get_case(case_id)
    if case is None:
        return jsonify({"error": "Case not found"}), 404

    progress = state_machine.compute_progress(
        case["case_type"], case["current_stage"], case["stage_start_date"]
    )

    if not progress["eligible_to_advance"]:
        return jsonify({
            "error": "Case is not yet eligible to advance",
            "days_remaining": progress["days_remaining"],
        }), 400

    next_stage_id = progress["next_stage_id"]
    if next_stage_id is None:
        return jsonify({"error": "Case is already at its final stage"}), 400

    updated_case = case_model.update_case_stage(case_id, next_stage_id)
    new_progress = state_machine.compute_progress(
        updated_case["case_type"], updated_case["current_stage"], updated_case["stage_start_date"]
    )

    return jsonify({
        "case_id": updated_case["id"],
        "timeline": new_progress,
    })


@api.route("/case/<case_id>/news", methods=["GET"])
def get_case_news(case_id):
    """
    On-demand endpoint - called when the user asks about ongoing
    developments/updates related to their case. Not run automatically
    on every /analyze call, to keep that flow fast and cheap.
    """
    case = case_model.get_case(case_id)
    if case is None:
        return jsonify({"error": "Case not found"}), 404

    # Build a query hint from the case type - swap for a more specific
    # query if the user names an actual ongoing case/topic in their request
    query_hint = request.args.get("query", case["case_type"].replace("_", " "))

    news_articles = retrieve_news(query_hint)

    try:
        news_generated = generate_news_explanation(news_articles)
    except ValueError:
        news_generated = {"news_explanations": []}

    # Run through the same output filter as everything else
    safe_news = []
    for item in news_generated.get("news_explanations", []):
        text = item.get("plain_language", "")
        if contains_advisory_language(text):
            item["plain_language"] = FALLBACK_MESSAGE
            item["flagged"] = True
        safe_news.append(item)

    # Build news nodes for the graph
    news_nodes = []
    for article in news_articles:
        explanation = next(
            (e["plain_language"] for e in safe_news if e["id"] == article["id"]),
            article["text"]
        )
        news_nodes.append({
            "id": article["id"],
            "label": article["title"],
            "type": "news",
            "detail": explanation,
            "source_name": article["source_name"],
            "source_url": article["source_url"],
            "published_at": article["published_at"],
        })

    return jsonify({
        "case_id": case_id,
        "news_nodes": news_nodes,
    })
