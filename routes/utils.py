import json
import re
from functools import wraps
from datetime import datetime
from flask import request, jsonify, redirect, session
from werkzeug.security import check_password_hash
from config.database import get_connection

ADMIN_USERNAME = "shivraj"
ADMIN_PASSWORD = "shivrajsinghania766@$"
ADMIN_PASSWORD_HASH = ""

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect("/admin/login")
        return view_func(*args, **kwargs)
    return wrapper

def _admin_password_ok(password):
    if ADMIN_PASSWORD_HASH:
        return check_password_hash(ADMIN_PASSWORD_HASH, password)
    return bool(ADMIN_PASSWORD) and password == ADMIN_PASSWORD

def _parse_json_list(text):
    raw = (text or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        return [parsed]
    except Exception:
        return [line.strip(" -•\t") for line in raw.splitlines() if line.strip()]

def _service_for_form(record=None):
    record = dict(record or {})
    record.setdefault("service_key", "")
    record.setdefault("service_name", "")
    record.setdefault("state", "")
    record.setdefault("jurisdiction_type", "state")
    record.setdefault("category", "")
    record.setdefault("icon", "")
    record.setdefault("department", "")
    record.setdefault("portal_name", "")
    record.setdefault("portal_url", "")
    record.setdefault("apply_url", "")
    record.setdefault("eligibility", "")
    record.setdefault("fees", "")
    record.setdefault("timeline", "")
    record.setdefault("photo_size", "")
    record.setdefault("signature_size", "")
    record.setdefault("upload_limits", "")
    record.setdefault("validity", "")
    record.setdefault("notes", "")
    record.setdefault("confidence_score", 0)
    record.setdefault("last_verified", "")
    record.setdefault("manual_review_needed", False)
    record.setdefault("active", True)
    record["documents_json_text"] = json.dumps(record.get("documents", []), ensure_ascii=False, indent=2)
    record["steps_json_text"] = json.dumps(record.get("steps", []), ensure_ascii=False, indent=2)
    record["sources_json_text"] = json.dumps(record.get("sources", []), ensure_ascii=False, indent=2)
    return record

def _payload_from_form(form, service_key=None):
    return {
        "service_key": service_key or form.get("service_key") or "",
        "service_name": form.get("service_name", "").strip(),
        "state": form.get("state", "").strip(),
        "jurisdiction_type": form.get("jurisdiction_type", "state").strip(),
        "category": form.get("category", "").strip(),
        "icon": form.get("icon", "").strip(),
        "department": form.get("department", "").strip(),
        "portal_name": form.get("portal_name", "").strip(),
        "portal_url": form.get("portal_url", "").strip(),
        "apply_url": form.get("apply_url", "").strip(),
        "documents_json": _parse_json_list(form.get("documents_json")),
        "eligibility": form.get("eligibility", "").strip(),
        "fees": form.get("fees", "").strip(),
        "timeline": form.get("timeline", "").strip(),
        "photo_size": form.get("photo_size", "").strip(),
        "signature_size": form.get("signature_size", "").strip(),
        "upload_limits": form.get("upload_limits", "").strip(),
        "validity": form.get("validity", "").strip(),
        "application_steps_json": _parse_json_list(form.get("steps_json")),
        "notes": form.get("notes", "").strip(),
        "sources_json": _parse_json_list(form.get("sources_json")),
        "confidence_score": int(form.get("confidence_score") or 0),
        "last_verified": form.get("last_verified", "").strip(),
        "manual_review_needed": form.get("manual_review_needed") == "on",
        "active": form.get("active") == "on",
    }

def _as_list(value):
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return _parse_json_list(value)

def _payload_from_json(data, service_key=None):
    data = data or {}
    return {
        "service_key": service_key or data.get("service_key") or "",
        "service_name": str(data.get("service_name") or "").strip(),
        "state": str(data.get("state") or "").strip(),
        "jurisdiction_type": str(data.get("jurisdiction_type") or "state").strip(),
        "category": str(data.get("category") or "").strip(),
        "icon": str(data.get("icon") or "").strip(),
        "department": str(data.get("department") or "").strip(),
        "portal_name": str(data.get("portal_name") or "").strip(),
        "portal_url": str(data.get("portal_url") or "").strip(),
        "apply_url": str(data.get("apply_url") or "").strip(),
        "documents_json": _as_list(data.get("documents")),
        "eligibility": str(data.get("eligibility") or "").strip(),
        "fees": str(data.get("fees") or "").strip(),
        "timeline": str(data.get("timeline") or "").strip(),
        "photo_size": str(data.get("photo_size") or "").strip(),
        "signature_size": str(data.get("signature_size") or "").strip(),
        "upload_limits": str(data.get("upload_limits") or "").strip(),
        "validity": str(data.get("validity") or "").strip(),
        "application_steps_json": _as_list(data.get("steps")),
        "notes": str(data.get("notes") or "").strip(),
        "sources_json": _as_list(data.get("sources")),
        "confidence_score": int(data.get("confidence_score") or 0),
        "last_verified": str(data.get("last_verified") or "").strip(),
        "manual_review_needed": bool(data.get("manual_review_needed")),
        "active": bool(data.get("active", True)),
    }

def _service_json(record, variant_keys=None):
    record = record or {}
    return {
        "service_key": record.get("service_key") or "",
        "service_name": record.get("service_name") or "",
        "state": record.get("state") or "",
        "jurisdiction_type": record.get("jurisdiction_type") or "state",
        "category": record.get("category") or "",
        "icon": record.get("icon") or "",
        "department": record.get("department") or "",
        "portal_name": record.get("portal_name") or "",
        "portal_url": record.get("portal_url") or "",
        "apply_url": record.get("apply_url") or "",
        "documents": record.get("documents") or [],
        "eligibility": record.get("eligibility") or "",
        "fees": record.get("fees") or "",
        "timeline": record.get("timeline") or "",
        "photo_size": record.get("photo_size") or "",
        "signature_size": record.get("signature_size") or "",
        "upload_limits": record.get("upload_limits") or "",
        "validity": record.get("validity") or "",
        "steps": record.get("steps") or [],
        "notes": record.get("notes") or "",
        "sources": record.get("sources") or [],
        "confidence_score": record.get("confidence_score") or 0,
        "last_verified": record.get("last_verified") or "",
        "manual_review_needed": bool(record.get("manual_review_needed")),
        "active": bool(record.get("active", True)),
        "has_variants": (record.get("service_key") in variant_keys) if variant_keys is not None else False,
    }

def _variant_json(record):
    record = record or {}
    return {
        "id": record.get("id"),
        "parent_service_key": record.get("parent_service_key") or "",
        "parent_variant_id": record.get("parent_variant_id"),
        "variant_key": record.get("variant_key") or "",
        "label": record.get("label") or "",
        "icon": record.get("icon") or "",
        "department": record.get("department") or "",
        "portal_name": record.get("portal_name") or "",
        "portal_url": record.get("portal_url") or "",
        "apply_url": record.get("apply_url") or "",
        "documents": record.get("documents") or [],
        "eligibility": record.get("eligibility") or "",
        "fees": record.get("fees") or "",
        "timeline": record.get("timeline") or "",
        "photo_size": record.get("photo_size") or "",
        "signature_size": record.get("signature_size") or "",
        "upload_limits": record.get("upload_limits") or "",
        "validity": record.get("validity") or "",
        "steps": record.get("steps") or [],
        "notes": record.get("notes") or "",
        "sources": record.get("sources") or [],
        "sort_order": record.get("sort_order") or 0,
        "active": bool(record.get("active", True)),
        "has_children": bool(record.get("has_children", False)),
    }

def _variant_payload_from_json(data):
    data = data or {}
    return {
        "id": data.get("id"),
        "parent_variant_id": data.get("parent_variant_id"),
        "variant_key": str(data.get("variant_key") or "").strip(),
        "label": str(data.get("label") or "").strip(),
        "icon": str(data.get("icon") or "").strip(),
        "department": str(data.get("department") or "").strip(),
        "portal_name": str(data.get("portal_name") or "").strip(),
        "portal_url": str(data.get("portal_url") or "").strip(),
        "apply_url": str(data.get("apply_url") or "").strip(),
        "documents": _as_list(data.get("documents")),
        "eligibility": str(data.get("eligibility") or "").strip(),
        "fees": str(data.get("fees") or "").strip(),
        "timeline": str(data.get("timeline") or "").strip(),
        "photo_size": str(data.get("photo_size") or "").strip(),
        "signature_size": str(data.get("signature_size") or "").strip(),
        "upload_limits": str(data.get("upload_limits") or "").strip(),
        "validity": str(data.get("validity") or "").strip(),
        "steps": _as_list(data.get("steps")),
        "notes": str(data.get("notes") or "").strip(),
        "sources": _as_list(data.get("sources")),
        "sort_order": int(data.get("sort_order") or 0),
        "active": bool(data.get("active", True)),
    }

def normalize_gmail_email(local_part: str) -> str:
    local_part = (local_part or "").strip().lower()
    local_part = local_part.replace(" ", "")
    if local_part.endswith("@gmail.com"):
        local_part = local_part.replace("@gmail.com", "")
    return f"{local_part}@gmail.com" if local_part else ""

def add_user(email, username, hashed_password):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users(email, username, password) VALUES(%s, %s, %s)",
            (email, username, hashed_password)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return "success"
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return "exists"
        raise

def validate_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, username, password FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        stored_hash = user[3]
        return check_password_hash(stored_hash, password)
    return False

def save_history(user_id, task, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO history(user_id, action, app, target, message, query, status)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (user_id, task.get("action"), task.get("app"), task.get("target"), task.get("message"), task.get("query"), status))
    conn.commit()
    cursor.close()
    conn.close()

def save_result(user_id, task_id, action, result):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO task_results(user_id, task_id, action, result_json)
    VALUES(%s, %s, %s, %s)
    """, (user_id, task_id, action, json.dumps(result)))
    conn.commit()
    cursor.close()
    conn.close()

def create_chat_session(user_id, title):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_sessions(user_id, title) VALUES (%s, %s) RETURNING id", (user_id, title))
    chat_session_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return chat_session_id

def save_chat_message(session_id, user_id, role, content):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO chat_messages(session_id, user_id, role, content)
    VALUES (%s, %s, %s, %s)
    """, (session_id, user_id, role, content))
    cursor.execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=%s", (session_id,))
    conn.commit()
    cursor.close()
    conn.close()

def research_summary_text(r):
    a = r.get("analysis", {}) or {}
    service_name = a.get("service_name") or (r.get("service") or "").replace("_", " ")
    state_name = a.get("state") or r.get("state", "")
    return f"Research completed for {service_name} in {state_name}. User is applying in {state_name}."

def needs_subtype_summary_text(service_name, subtypes):
    labels = ", ".join(s.get("label", "") for s in subtypes)
    return f"What type of {service_name} do you need? Options: {labels}"

def observe_summary_text(obs):
    analysis = (obs.get("analysis") or "")[:100]
    return f"Observed {obs.get('url', '')}: {analysis}"

def workflow_summary_text(tasks):
    actions = ", ".join(t.get("action", "") for t in tasks)
    return f"Workflow created with {len(tasks)} step(s): {actions}"

def create_workflow(user_id, tasks):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO workflows (user_id, workflow_json, status, current_step, started_at)
    VALUES (%s, %s, %s, %s, %s) RETURNING id
    """, (user_id, json.dumps(tasks), "running", 0, datetime.now()))
    workflow_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return workflow_id

def update_workflow_step(workflow_id, step):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE workflows SET current_step=%s WHERE id=%s", (step, workflow_id))
    conn.commit()
    cursor.close()
    conn.close()

def complete_workflow(workflow_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE workflows SET status=%s, completed_at=%s WHERE id=%s", ("completed", datetime.now(), workflow_id))
    conn.commit()
    cursor.close()
    conn.close()

def add_task(user_id, task):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO task_queue(user_id, task_json, status, attempts)
    VALUES (%s, %s, %s, %s) RETURNING id
    """, (user_id, json.dumps(task), "pending", 0))
    task_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return task_id

def mark_running(task_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE task_queue SET status=%s, started_at=%s WHERE id=%s", ("running", datetime.now(), task_id))
    conn.commit()
    cursor.close()
    conn.close()

def mark_completed(task_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE task_queue SET status=%s, completed_at=%s WHERE id=%s", ("completed", datetime.now(), task_id))
    conn.commit()
    cursor.close()
    conn.close()

def mark_failed(task_id, error):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE task_queue SET status=%s, error=%s, attempts=attempts+1 WHERE id=%s", ("failed", str(error), task_id))
    conn.commit()
    cursor.close()
    conn.close()
