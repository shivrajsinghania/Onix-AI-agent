from flask import Blueprint, request, jsonify, render_template, redirect, session
from tools.knowledge import (
    list_public_services, get_service_knowledge, list_service_variants, 
    resolve_variant_content, build_research_payload, get_service_variant
)
from routes.utils import save_history

task_bp = Blueprint("task", __name__)

@task_bp.route("/agent")
def home():
    if "user" not in session: return redirect("/login-page")
    return render_template("agent.html")

@task_bp.route("/api/services")
def api_services():
    state = (request.args.get("state") or "").strip() or None
    try:
        groups = list_public_services(state=state)
        return jsonify({"status": "success", "groups": groups})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@task_bp.route("/api/service-variants")
def api_service_variants():
    service_key = (request.args.get("service") or "").strip()
    if not service_key: return jsonify({"status": "error", "message": "Missing service"}), 400

    record = get_service_knowledge(service_key)
    if not record or not record.get("active", True):
        return jsonify({"status": "error", "message": "Service not found"}), 404

    try:
        variants = list_service_variants(service_key, active_only=True)
        items = [{"id": v["id"], "label": v["label"], "icon": v.get("icon") or "📄"} for v in variants]
        return jsonify({"status": "success", "variants": items})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@task_bp.route("/task/ask", methods=["POST"])
def task_ask():
    if "user" not in session: return jsonify({"error": "Unauthorized"}), 401

    user_data = request.get_json(silent=True) or {}
    question = (user_data.get("message") or "").strip()
    user_id = session["user_id"]
    
    service = (user_data.get("service") or "").strip()
    state = (user_data.get("state") or "").strip()
    variant_id = user_data.get("variant_id")

    if not service or not state:
        return jsonify({"status": "error", "message": "Missing service or state"}), 400

    record = get_service_knowledge(service, state)
    if not record or not record.get("active", True):
        save_history(user_id, {"action": "knowledge_lookup", "app": "service_knowledge", "target": service, "message": state, "query": question}, "missing")
        return jsonify({"status": "missing", "message": "This service is not in the database yet. Add it from admin panel."}), 404

    if variant_id:
        merged = resolve_variant_content(record.get("service_key"), int(variant_id))
        if not merged: return jsonify({"status": "error", "message": "Variant not found"}), 404
        research = build_research_payload(merged)
        save_history(user_id, {"action": "knowledge_lookup", "app": "service_knowledge", "target": research.get("analysis", {}).get("service_name") or service, "message": research.get("state") or state, "query": question}, "served")
        return jsonify({"status": "research", "research": research, "remember": {"state": research.get("state", state)}, "session_id": None})

    top_level_variants = list_service_variants(record.get("service_key"), active_only=True)
    if top_level_variants:
        subtypes = [{"id": v["id"], "label": v["label"], "description": ""} for v in top_level_variants]
        save_history(user_id, {"action": "knowledge_lookup", "app": "service_knowledge", "target": record.get("service_name") or service, "message": state, "query": question}, "needs_subtype")
        return jsonify({"status": "needs_subtype", "service": record.get("service_key"), "service_name": record.get("service_name"), "subtypes": subtypes, "session_id": None})

    research = build_research_payload(record)
    save_history(user_id, {"action": "knowledge_lookup", "app": "service_knowledge", "target": research.get("analysis", {}).get("service_name") or service, "message": research.get("state") or state, "query": question}, "served")
    return jsonify({"status": "research", "research": research, "remember": {"state": research.get("state", state)}, "session_id": None})

@task_bp.route("/research-subtype", methods=["POST"])
def research_subtype():
    if "user" not in session: return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    service = (data.get("service") or "").strip()
    state = (data.get("state") or "").strip()
    subtype = data.get("subtype")
    chat_session_id = data.get("session_id")

    if not service or not state: return jsonify({"status": "error", "message": "Missing service or state"}), 400
    if not subtype: return jsonify({"status": "error", "message": "Missing subtype"}), 400

    record = get_service_knowledge(service, state)
    if not record or not record.get("active", True): return jsonify({"status": "missing", "message": "Not in database yet"}), 404

    try:
        variant_id = int(subtype)
    except (TypeError, ValueError): return jsonify({"status": "error", "message": "Invalid subtype"}), 400

    variant = get_service_variant(variant_id)
    if not variant or not variant.get("active", True): return jsonify({"status": "missing", "message": "Subtype not found"}), 404

    merged = resolve_variant_content(record.get("service_key"), variant_id)
    if not merged: return jsonify({"status": "missing", "message": "Not in database yet"}), 404

    research = build_research_payload(merged)
    save_history(session["user_id"], {"action": "knowledge_lookup", "app": "service_knowledge", "target": research.get("analysis", {}).get("service_name") or service, "message": research.get("state") or state, "query": f"subtype:{variant.get('label')}"}, "served")
    return jsonify({"status": "research", "research": research, "remember": {"state": state}, "session_id": chat_session_id})