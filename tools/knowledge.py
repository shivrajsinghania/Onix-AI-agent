import json
import re
from datetime import datetime, timedelta
import psycopg2.extras

from config.database import get_connection

def _ensure_schema_updates():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE service_knowledge ADD COLUMN IF NOT EXISTS has_variants INTEGER DEFAULT 0")

    columns_to_add = [
        ("icon", "TEXT"), ("department", "TEXT"), ("portal_name", "TEXT"),
        ("portal_url", "TEXT"), ("apply_url", "TEXT"), ("documents_json", "TEXT DEFAULT '[]'"),
        ("eligibility", "TEXT"), ("fees", "TEXT"), ("timeline", "TEXT"),
        ("photo_size", "TEXT"), ("signature_size", "TEXT"), ("upload_limits", "TEXT"),
        ("validity", "TEXT"), ("application_steps_json", "TEXT DEFAULT '[]'"), ("notes", "TEXT"),
        ("sources_json", "TEXT DEFAULT '[]'"), ("last_verified", "TEXT"),
        ("manual_review_needed", "INTEGER DEFAULT 0")
    ]

    for col_name, col_type in columns_to_add:
        cursor.execute(f"ALTER TABLE service_variants ADD COLUMN IF NOT EXISTS {col_name} {col_type}")

    conn.commit()
    cursor.close()
    conn.close()

_ensure_schema_updates()

def _slugify(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")

def _parse_json(value, default):
    if value is None or value == "": return default
    if isinstance(value, (list, dict)): return value
    try: return json.loads(value)
    except Exception: return default

def _row_to_record(row):
    if row is None: return None
    record = dict(row)
    record["documents"] = _parse_json(record.pop("documents_json", "[]"), [])
    record["steps"] = _parse_json(record.pop("application_steps_json", "[]"), [])
    record["sources"] = _parse_json(record.pop("sources_json", "[]"), [])
    record["manual_review_needed"] = bool(record.get("manual_review_needed", 0))
    record["has_variants"] = bool(record.get("has_variants", 0))
    record["active"] = bool(record.get("active", 1))
    return record

def _service_key_from_data(data):
    key = data.get("service_key") or data.get("service_name") or data.get("service") or ""
    return _slugify(key)

def _service_name_from_key(service_key):
    return str(service_key or "").replace("-", " ").strip().title() or "Unnamed Service"

def _jurisdiction_type(state, incoming=None):
    if incoming: return str(incoming).strip().lower()
    state_text = str(state or "").strip().lower()
    if state_text in {"central", "india", "all india", "pan india"}: return "central"
    return "state"

_CONFIDENCE_FIELD_WEIGHTS = {
    "department": 8, "portal_name": 8, "portal_url": 8, "apply_url": 6,
    "eligibility": 8, "fees": 8, "timeline": 8, "validity": 6, "category": 4,
}

def _compute_confidence_score(payload):
    score = 0
    for field, weight in _CONFIDENCE_FIELD_WEIGHTS.items():
        if str(payload.get(field) or "").strip(): score += weight
    if payload.get("documents"): score += 12
    if payload.get("steps"): score += 12
    if payload.get("sources"): score += 8
    if str(payload.get("photo_size") or "").strip(): score += 3
    if str(payload.get("signature_size") or "").strip(): score += 3
    if str(payload.get("upload_limits") or "").strip(): score += 2
    if str(payload.get("notes") or "").strip(): score += 2
    if str(payload.get("last_verified") or "").strip(): score += 4
    if payload.get("manual_review_needed"): score -= 5
    return max(0, min(100, score))

def get_service_knowledge(service, state=None):
    service_text = str(service or "").strip()
    if not service_text: return None
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    key = _slugify(service_text)
    if state:
        cursor.execute("SELECT * FROM service_knowledge WHERE lower(service_key)=lower(%s) OR (lower(service_name)=lower(%s) AND lower(state)=lower(%s)) LIMIT 1", (key, service_text, str(state).strip()))
    else:
        cursor.execute("SELECT * FROM service_knowledge WHERE lower(service_key)=lower(%s) OR lower(service_name)=lower(%s) LIMIT 1", (key, service_text))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return _row_to_record(row)

def list_service_knowledge(state=None, category=None, query=None, active=None, limit=200):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    sql = "SELECT * FROM service_knowledge WHERE 1=1"
    params = []
    if state:
        sql += " AND lower(state)=lower(%s)"
        params.append(str(state).strip())
    if category:
        sql += " AND lower(category)=lower(%s)"
        params.append(str(category).strip())
    if active is not None:
        sql += " AND active=%s"
        params.append(1 if active else 0)
    if query:
        q = f"%{str(query).strip().lower()}%"
        sql += " AND (lower(service_name) LIKE %s OR lower(service_key) LIKE %s OR lower(portal_name) LIKE %s OR lower(department) LIKE %s OR lower(notes) LIKE %s)"
        params.extend([q, q, q, q, q])
    sql += " ORDER BY active DESC, state ASC, category ASC, service_name ASC"
    if limit:
        sql += " LIMIT %s"
        params.append(int(limit))
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [_row_to_record(row) for row in rows]

def list_public_services(state=None):
    records = list_service_knowledge(state=state, active=True, limit=1000)
    variant_keys = _service_keys_with_variants()
    groups = {}
    order = []
    for r in records:
        group_name = r.get("category") or "Other"
        if group_name not in groups:
            groups[group_name] = []
            order.append(group_name)

        has_vars = bool(r.get("has_variants")) or (r.get("service_key") in variant_keys)

        groups[group_name].append({
            "value": r.get("service_key"),
            "label": r.get("service_name"),
            "icon": r.get("icon") or "📄",
            "has_variants": has_vars,
        })
    return [{"group": name, "items": groups[name]} for name in order]

def get_due_service_reviews(days=7):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute(
        """SELECT service_name, state, last_verified FROM service_knowledge
        WHERE active=1 AND has_variants=0
        AND (manual_review_needed=1 OR last_verified IS NULL OR TRIM(last_verified) = ''
        OR last_verified::date <= CURRENT_DATE - %s::integer * INTERVAL '1 day')""",
        (int(days),)
    )
    parents = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """SELECT sv.label as name, sk.service_name as parent_name, sk.state, sv.last_verified
        FROM service_variants sv JOIN service_knowledge sk ON sv.parent_service_key = sk.service_key
        WHERE sv.active=1
        AND (sv.manual_review_needed=1 OR sv.last_verified IS NULL OR TRIM(sv.last_verified) = ''
        OR sv.last_verified::date <= CURRENT_DATE - %s::integer * INTERVAL '1 day')""",
        (int(days),)
    )
    variants = []
    for row in cursor.fetchall():
        variants.append({
            "service_name": f"{row['parent_name']} - {row['name']}",
            "state": row["state"],
            "last_verified": row["last_verified"]
        })

    cursor.close()
    conn.close()
    combined = parents + variants
    combined.sort(key=lambda x: x["last_verified"] or "")
    return combined

def save_service_knowledge(data, changed_by=None):
    service_key = _service_key_from_data(data)
    if not service_key: raise ValueError("service_key or service_name is required")

    service_name = str(data.get("service_name") or data.get("service") or _service_name_from_key(service_key)).strip()
    state = str(data.get("state") or "Central").strip() or "Central"
    jurisdiction_type = _jurisdiction_type(state, data.get("jurisdiction_type"))
    category = (data.get("category") or "").strip() or None
    icon = (data.get("icon") or "").strip() or None
    department = (data.get("department") or "").strip() or None
    portal_name = (data.get("portal_name") or "").strip() or None
    portal_url = (data.get("portal_url") or "").strip() or None
    apply_url = (data.get("apply_url") or "").strip() or None
    eligibility = (data.get("eligibility") or "").strip() or None
    fees = (data.get("fees") or "").strip() or None
    timeline = (data.get("timeline") or "").strip() or None
    photo_size = (data.get("photo_size") or "").strip() or None
    signature_size = (data.get("signature_size") or "").strip() or None
    upload_limits = (data.get("upload_limits") or "").strip() or None
    validity = (data.get("validity") or "").strip() or None
    notes = (data.get("notes") or "").strip() or None
    sources = data.get("sources") or data.get("sources_json") or []
    documents = data.get("documents") or data.get("documents_json") or []
    steps = data.get("steps") or data.get("application_steps_json") or []
    last_verified = (data.get("last_verified") or "").strip() or None
    manual_review_needed = 1 if data.get("manual_review_needed") else 0
    has_variants = 1 if data.get("has_variants") else 0
    active = 1 if data.get("active", True) else 0

    confidence_score = _compute_confidence_score({"department": department, "portal_name": portal_name, "portal_url": portal_url, "apply_url": apply_url, "eligibility": eligibility, "fees": fees, "timeline": timeline, "validity": validity, "category": category, "photo_size": photo_size, "signature_size": signature_size, "upload_limits": upload_limits, "notes": notes, "documents": documents, "steps": steps, "sources": sources, "last_verified": last_verified, "manual_review_needed": bool(manual_review_needed)})
    updated_by = (changed_by or data.get("updated_by") or "").strip() or None
    change_summary = (data.get("change_summary") or "").strip() or None

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("SELECT version FROM service_knowledge WHERE service_key=%s LIMIT 1", (service_key,))
    existing = cursor.fetchone()
    version = int(existing["version"]) + 1 if existing else 1

    snapshot = {
        "service_key": service_key, "service_name": service_name, "state": state, "jurisdiction_type": jurisdiction_type, "category": category, "icon": icon, "department": department, "portal_name": portal_name, "portal_url": portal_url, "apply_url": apply_url, "documents": documents, "eligibility": eligibility, "fees": fees, "timeline": timeline, "photo_size": photo_size, "signature_size": signature_size, "upload_limits": upload_limits, "validity": validity, "steps": steps, "notes": notes, "sources": sources, "confidence_score": confidence_score, "last_verified": last_verified, "manual_review_needed": bool(manual_review_needed), "has_variants": bool(has_variants), "active": bool(active), "version": version, "updated_by": updated_by, "saved_at": datetime.utcnow().isoformat(timespec="seconds"),
    }

    if existing:
        cursor.execute(
            """UPDATE service_knowledge SET service_name=%s, state=%s, jurisdiction_type=%s, category=%s, icon=%s, department=%s, portal_name=%s, portal_url=%s, apply_url=%s, documents_json=%s, eligibility=%s, fees=%s, timeline=%s, photo_size=%s, signature_size=%s, upload_limits=%s, validity=%s, application_steps_json=%s, notes=%s, sources_json=%s, confidence_score=%s, last_verified=%s, manual_review_needed=%s, has_variants=%s, active=%s, version=%s, updated_by=%s, updated_at=CURRENT_TIMESTAMP WHERE service_key=%s""",
            (service_name, state, jurisdiction_type, category, icon, department, portal_name, portal_url, apply_url, json.dumps(documents, ensure_ascii=False), eligibility, fees, timeline, photo_size, signature_size, upload_limits, validity, json.dumps(steps, ensure_ascii=False), notes, json.dumps(sources, ensure_ascii=False), confidence_score, last_verified, manual_review_needed, has_variants, active, version, updated_by, service_key)
        )
    else:
        cursor.execute(
            """INSERT INTO service_knowledge(service_key, service_name, state, jurisdiction_type, category, icon, department, portal_name, portal_url, apply_url, documents_json, eligibility, fees, timeline, photo_size, signature_size, upload_limits, validity, application_steps_json, notes, sources_json, confidence_score, last_verified, manual_review_needed, has_variants, active, version, updated_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (service_key, service_name, state, jurisdiction_type, category, icon, department, portal_name, portal_url, apply_url, json.dumps(documents, ensure_ascii=False), eligibility, fees, timeline, photo_size, signature_size, upload_limits, validity, json.dumps(steps, ensure_ascii=False), notes, json.dumps(sources, ensure_ascii=False), confidence_score, last_verified, manual_review_needed, has_variants, active, version, updated_by)
        )

    cursor.execute("INSERT INTO service_versions(service_key, version, snapshot_json, change_summary, changed_by) VALUES(%s,%s,%s,%s,%s)", (service_key, version, json.dumps(snapshot, ensure_ascii=False), change_summary, updated_by))
    conn.commit()
    cursor.close()
    conn.close()
    return get_service_knowledge(service_key)

def public_service_card(record):
    if not record: return None
    documents = record.get("documents") or []
    steps = record.get("steps") or []
    return {
        "service_key": record.get("service_key"), "service_name": record.get("service_name"), "state": record.get("state"), "jurisdiction_type": record.get("jurisdiction_type"), "category": record.get("category"), "department": record.get("department"), "portal_name": record.get("portal_name"), "portal_url": record.get("portal_url"), "apply_url": record.get("apply_url"), "documents": documents[:8], "eligibility": record.get("eligibility"), "fees": record.get("fees"), "timeline": record.get("timeline"), "photo_size": record.get("photo_size"), "signature_size": record.get("signature_size"), "upload_limits": record.get("upload_limits"), "validity": record.get("validity"), "steps": steps[:8], "notes": record.get("notes"), "active": bool(record.get("active", True)),
    }

def build_research_payload(record):
    if not record: return None
    documents = record.get("documents") or []
    steps = record.get("steps") or []
    sources = record.get("sources") or []
    analysis = {
        "service_name": record.get("service_name") or "", "state": record.get("state") or "", "department": record.get("department") or "", "portal_name": record.get("portal_name") or "", "portal_url": record.get("portal_url") or "", "apply_url": record.get("apply_url") or "", "fee": record.get("fees") or "", "processing_time": record.get("timeline") or "", "eligibility": record.get("eligibility") or "", "validity": record.get("validity") or "", "upload_limits": record.get("upload_limits") or "", "last_verified": record.get("last_verified") or "", "required_documents": documents, "application_steps": steps, "faq": [], "notes": record.get("notes") or "", "extra_important_items": [], "sources": sources, "pdf_sources": [], "photo_size": record.get("photo_size") or "", "signature_size": record.get("signature_size") or "",
    }
    return { "service": record.get("service_key") or record.get("service_name") or "", "state": record.get("state") or "", "url": record.get("portal_url") or record.get("apply_url") or "", "analysis": analysis }

_VARIANT_CONTENT_FIELDS = [
    "icon", "department", "portal_name", "portal_url", "apply_url",
    "eligibility", "fees", "timeline", "photo_size", "signature_size",
    "upload_limits", "validity", "notes",
]

def _row_to_variant(row):
    if row is None: return None
    record = dict(row)
    record["documents"] = _parse_json(record.pop("documents_json", None), [])
    record["steps"] = _parse_json(record.pop("application_steps_json", None), [])
    record["sources"] = _parse_json(record.pop("sources_json", None), [])
    record["manual_review_needed"] = bool(record.get("manual_review_needed", 0))
    record["active"] = bool(record.get("active", 1))
    return record

def _service_keys_with_variants():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT parent_service_key FROM service_variants WHERE active=1")
    keys = {row[0] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return keys

def service_keys_with_variants(): return _service_keys_with_variants()

def service_keys_with_any_variants():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT parent_service_key FROM service_variants")
    keys = {row[0] for row in cursor.fetchall()}
    cursor.close()
    conn.close()
    return keys

def list_service_variants(service_key, active_only=True):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    sql = "SELECT * FROM service_variants WHERE parent_service_key=lower(%s)"
    if active_only: sql += " AND active=1"
    sql += " ORDER BY sort_order ASC, label ASC"
    cursor.execute(sql, [_slugify(service_key)])
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [_row_to_variant(row) for row in rows]

def get_service_variant(variant_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM service_variants WHERE id=%s", (int(variant_id),))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return _row_to_variant(row)

def resolve_variant_content(service_key, variant_id):
    base = get_service_knowledge(service_key)
    if not base: return None
    variant = get_service_variant(variant_id)
    if not variant: return base

    merged = dict(base)
    for field in _VARIANT_CONTENT_FIELDS:
        if str(variant.get(field) or "").strip():
            merged[field] = variant[field]
    if variant.get("documents"): merged["documents"] = variant["documents"]
    if variant.get("steps"): merged["steps"] = variant["steps"]
    if variant.get("sources"): merged["sources"] = variant["sources"]
    merged["service_name"] = f"{base.get('service_name')} - {variant.get('label')}"
    return merged

def save_service_variant(data, parent_service_key=None, changed_by=None):
    service_key = _slugify(parent_service_key or data.get("parent_service_key") or "")
    if not service_key: raise ValueError("parent_service_key is required")
    label = str(data.get("label") or "").strip()
    if not label: raise ValueError("label is required")

    variant_key = _slugify(data.get("variant_key") or label)
    icon = (data.get("icon") or "").strip() or None
    department = (data.get("department") or "").strip() or None
    portal_name = (data.get("portal_name") or "").strip() or None
    portal_url = (data.get("portal_url") or "").strip() or None
    apply_url = (data.get("apply_url") or "").strip() or None
    eligibility = (data.get("eligibility") or "").strip() or None
    fees = (data.get("fees") or "").strip() or None
    timeline = (data.get("timeline") or "").strip() or None
    photo_size = (data.get("photo_size") or "").strip() or None
    signature_size = (data.get("signature_size") or "").strip() or None
    upload_limits = (data.get("upload_limits") or "").strip() or None
    validity = (data.get("validity") or "").strip() or None
    notes = (data.get("notes") or "").strip() or None
    documents = data.get("documents") or []
    steps = data.get("steps") or []
    sources = data.get("sources") or []
    sort_order = int(data.get("sort_order") or 0)
    last_verified = (data.get("last_verified") or "").strip() or None
    manual_review_needed = 1 if data.get("manual_review_needed") else 0
    active = 1 if data.get("active", True) else 0
    variant_id = data.get("id")

    conn = get_connection()
    cursor = conn.cursor()

    if variant_id:
        cursor.execute(
            """UPDATE service_variants SET variant_key=%s, label=%s, icon=%s, department=%s, portal_name=%s, portal_url=%s, apply_url=%s, documents_json=%s, eligibility=%s, fees=%s, timeline=%s, photo_size=%s, signature_size=%s, upload_limits=%s, validity=%s, application_steps_json=%s, notes=%s, sources_json=%s, sort_order=%s, active=%s, last_verified=%s, manual_review_needed=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s""",
            (variant_key, label, icon, department, portal_name, portal_url, apply_url, json.dumps(documents, ensure_ascii=False), eligibility, fees, timeline, photo_size, signature_size, upload_limits, validity, json.dumps(steps, ensure_ascii=False), notes, json.dumps(sources, ensure_ascii=False), sort_order, active, last_verified, manual_review_needed, int(variant_id))
        )
        result_id = int(variant_id)
    else:
        cursor.execute(
            """INSERT INTO service_variants(parent_service_key, variant_key, label, icon, department, portal_name, portal_url, apply_url, documents_json, eligibility, fees, timeline, photo_size, signature_size, upload_limits, validity, application_steps_json, notes, sources_json, sort_order, active, last_verified, manual_review_needed) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (service_key, variant_key, label, icon, department, portal_name, portal_url, apply_url, json.dumps(documents, ensure_ascii=False), eligibility, fees, timeline, photo_size, signature_size, upload_limits, validity, json.dumps(steps, ensure_ascii=False), notes, json.dumps(sources, ensure_ascii=False), sort_order, active, last_verified, manual_review_needed)
        )
        result_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()
    return get_service_variant(result_id)

def delete_service_variant(variant_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM service_variants WHERE id=%s", (int(variant_id),))
    conn.commit()
    cursor.close()
    conn.close()
    return 1