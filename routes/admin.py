from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, session, flash
from config.database import get_connection
from routes.utils import admin_required, _admin_password_ok, ADMIN_USERNAME
from tools.knowledge import (
    get_service_knowledge, list_service_knowledge, save_service_knowledge,
    get_due_service_reviews, list_service_variants, get_service_variant,
    save_service_variant, delete_service_variant, service_keys_with_any_variants,
    _VARIANT_CONTENT_FIELDS
)

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"): return redirect("/admin")
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if username == ADMIN_USERNAME and _admin_password_ok(password):
            session["is_admin"] = True
            session["admin_user"] = username
            return redirect("/admin")
        flash("Invalid admin credentials", "error")
    return render_template("admin_login.html")

@admin_bp.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    session.pop("admin_user", None)
    return redirect("/admin/login")

@admin_bp.route("/admin")
@admin_required
def admin_dashboard():
    q = (request.args.get("q") or "").strip()
    state = (request.args.get("state") or "").strip() or None
    services = list_service_knowledge(state=state, query=q or None, active=None, limit=300)
    due_reviews = get_due_service_reviews(days=7)
    return render_template("admin_dashboard.html", services=services, due_reviews=due_reviews, query=q, state=state)

@admin_bp.route("/admin/api/services")
@admin_required
def admin_api_services():
    q = (request.args.get("q") or "").strip()
    state = (request.args.get("state") or "").strip() or None
    services = list_service_knowledge(state=state, query=q or None, active=None, limit=300)
    due_reviews = get_due_service_reviews(days=7)
    return jsonify({
        "status": "success",
        "services": services,
        "due_reviews": due_reviews,
    })

@admin_bp.route("/admin/api/service/<path:service_key>")
@admin_required
def admin_api_service_get(service_key):
    record = get_service_knowledge(service_key)
    if not record: return jsonify({"status": "error", "message": "Service not found"}), 404
    return jsonify({"status": "success", "service": record})

@admin_bp.route("/admin/api/service/save", methods=["POST"])
@admin_required
def admin_api_service_save():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode") or "new"
    existing_key = (data.get("service_key") or "").strip() if mode == "edit" else None

    if mode == "edit" and not existing_key: return jsonify({"status": "error", "message": "Missing service_key"}), 400
    if not (data.get("service_name") or "").strip(): return jsonify({"status": "error", "message": "Service name is required"}), 400

    data["last_verified"] = datetime.now().strftime("%Y-%m-%d")
    if existing_key: data["service_key"] = existing_key

    try:
        record = save_service_knowledge(data, changed_by=session.get("admin_user"))
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    return jsonify({"status": "success", "service": record})

@admin_bp.route("/admin/api/service/<path:service_key>/delete", methods=["POST"])
@admin_required
def admin_api_service_delete(service_key):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE service_knowledge SET active=0, updated_at=CURRENT_TIMESTAMP WHERE service_key=%s", (service_key,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success"})

@admin_bp.route("/admin/api/service/<path:service_key>/restore", methods=["POST"])
@admin_required
def admin_api_service_restore(service_key):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE service_knowledge SET active=1, updated_at=CURRENT_TIMESTAMP WHERE service_key=%s", (service_key,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success"})

@admin_bp.route("/admin/api/service/<path:service_key>/variants")
@admin_required
def admin_api_service_variants(service_key):
    record = get_service_knowledge(service_key)
    if not record: return jsonify({"status": "error", "message": "Service not found"}), 404
    variants = list_service_variants(service_key, active_only=False)
    return jsonify({
        "status": "success",
        "variants": variants,
    })

@admin_bp.route("/admin/api/service/<path:service_key>/variant/<int:variant_id>")
@admin_required
def admin_api_variant_get(service_key, variant_id):
    variant = get_service_variant(variant_id)
    if not variant: return jsonify({"status": "error", "message": "Variant not found"}), 404

    base = get_service_knowledge(service_key)
    if base:
        INHERIT_FIELDS = ["department", "portal_name", "portal_url", "apply_url",
                          "eligibility", "fees", "timeline", "photo_size",
                          "signature_size", "upload_limits", "validity", "notes"]
        merged = dict(variant)
        for field in INHERIT_FIELDS:
            if not str(variant.get(field) or "").strip() and str(base.get(field) or "").strip():
                merged[field] = base[field]
        for field in ("documents", "steps", "sources"):
            if not variant.get(field) and base.get(field):
                merged[field] = base[field]
        variant = merged

    return jsonify({"status": "success", "variant": variant})

@admin_bp.route("/admin/api/service/<path:service_key>/variant/save", methods=["POST"])
@admin_required
def admin_api_variant_save(service_key):
    record = get_service_knowledge(service_key)
    if not record: return jsonify({"status": "error", "message": "Service not found"}), 404
    data = request.get_json(silent=True) or {}
    if not (data.get("label") or "").strip(): return jsonify({"status": "error", "message": "Label is required"}), 400

    data["last_verified"] = datetime.now().strftime("%Y-%m-%d")
    
    try:
        variant = save_service_variant(data, parent_service_key=service_key, changed_by=session.get("admin_user"))
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    return jsonify({"status": "success", "variant": variant})

@admin_bp.route("/admin/api/variant/<int:variant_id>/delete", methods=["POST"])
@admin_required
def admin_api_variant_delete(variant_id):
    variant = get_service_variant(variant_id)
    if not variant: return jsonify({"status": "error", "message": "Variant not found"}), 404
    delete_service_variant(variant_id)
    return jsonify({"status": "success"})
