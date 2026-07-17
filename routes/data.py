import json
from flask import Blueprint, jsonify, session
from config.database import get_connection

data_bp = Blueprint("data", __name__)

@data_bp.route("/history")
def history():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, action, app, target, message, query, status, created_at FROM history WHERE user_id=? ORDER BY id DESC", (session["user_id"],))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    data = [{"id": r[0], "action": r[1], "app": r[2], "target": r[3], "message": r[4], "query": r[5], "status": r[6], "created_at": str(r[7])} for r in rows]
    return jsonify(data)

@data_bp.route("/queue")
def queue():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM task_queue WHERE user_id=? ORDER BY id DESC", (session["user_id"],))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    data = [{"id": r[0], "task": json.loads(r[2]), "status": r[3], "attempts": r[4], "error": r[5], "started_at": str(r[6]), "completed_at": str(r[7]), "created_at": str(r[8])} for r in rows]
    return jsonify(data)

@data_bp.route("/workflows")
def workflows():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM workflows WHERE user_id=? ORDER BY id DESC", (session["user_id"],))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    data = [{"id": r[0], "workflow": json.loads(r[2]), "status": r[3], "current_step": r[4], "started_at": str(r[5]), "completed_at": str(r[6]), "created_at": str(r[7])} for r in rows]
    return jsonify(data)

@data_bp.route("/delete/<table>/<int:item_id>", methods=["DELETE"])
def delete_item(table, item_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    allowed_tables = {"history": "history", "queue": "task_queue", "workflow": "workflows", "results": "task_results"}
    if table not in allowed_tables:
        return jsonify({"status": "error", "message": "Invalid table"})
    
    real_table = allowed_tables[table]
    conn = get_connection()
    cursor = conn.cursor()
    query = f"DELETE FROM {real_table} WHERE id=? AND user_id=?"
    cursor.execute(query, (item_id, session["user_id"]))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success"})

@data_bp.route("/clear/<table>", methods=["DELETE"])
def clear_table(table):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    allowed_tables = {"history": "history", "queue": "task_queue", "workflow": "workflows", "results": "task_results"}
    if table not in allowed_tables:
        return jsonify({"status": "error", "message": "Invalid table"})
        
    real_table = allowed_tables[table]
    conn = get_connection()
    cursor = conn.cursor()
    query = f"DELETE FROM {real_table} WHERE user_id=?"
    cursor.execute(query, (session["user_id"],))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success"})

@data_bp.route("/results")
def results():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM task_results WHERE user_id=? ORDER BY id DESC", (session["user_id"],))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    data = [{"id": r[0], "task_id": r[2], "action": r[3], "result": json.loads(r[4]), "created_at": str(r[5])} for r in rows]
    return jsonify(data)
