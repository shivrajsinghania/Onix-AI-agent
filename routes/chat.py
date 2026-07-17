# chat.py
import json
from flask import Blueprint, request, jsonify, session
from tools.ai import ask_ai
from routes.utils import create_chat_session, save_chat_message, get_connection

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/chat/ask", methods=["POST"])
def chat_ask():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_data = request.get_json(silent=True) or {}
    question = (user_data.get("message") or "").strip()
    if not question:
        return jsonify({"error": "Message required"}), 400

    user_id = session["user_id"]
    history = user_data.get("history", [])[-15:]
    user_context = user_data.get("user_context", {})
    chat_session_id = user_data.get("session_id")

    if not chat_session_id:
        raw_title = question or "New chat"
        title = raw_title[:50] + ("…" if len(raw_title) > 50 else "")
        chat_session_id = create_chat_session(user_id, title)

    save_chat_message(chat_session_id, user_id, "user", question)
    response = ask_ai(question, history=history, user_context=user_context)

    try:
        workflow_data = json.loads(response)
        status = workflow_data.get("status")

        if status == "offline":
            ai_message = workflow_data.get("message", "Onix chat is temporarily offline.")
            save_chat_message(chat_session_id, user_id, "assistant", ai_message)
            return jsonify({"status": "offline", "message": ai_message, "session_id": chat_session_id})

        if status == "conversation":
            ai_message = workflow_data.get("message", "How can I help you?")
            save_chat_message(chat_session_id, user_id, "assistant", ai_message)
            return jsonify({"status": "conversation", "message": ai_message, "session_id": chat_session_id})

        if status == "need_clarification":
            question_text = workflow_data.get("question", "Can you clarify?")
            save_chat_message(chat_session_id, user_id, "assistant", question_text)
            return jsonify({"status": "need_clarification", "question": question_text, "session_id": chat_session_id})

        if status == "unsupported":
            msg = workflow_data.get("message", "This request is not supported.")
            save_chat_message(chat_session_id, user_id, "assistant", msg)
            return jsonify({"status": "unsupported", "message": msg, "session_id": chat_session_id})

        if "workflow" in workflow_data:
            msg = "For government-service research, please use Task mode and choose the service there."
            save_chat_message(chat_session_id, user_id, "assistant", msg)
            return jsonify({"status": "conversation", "message": msg, "session_id": chat_session_id})

        msg = "I can help with explanations and guidance here. For service research, please use Task mode."
        save_chat_message(chat_session_id, user_id, "assistant", msg)
        return jsonify({"status": "conversation", "message": msg, "session_id": chat_session_id})

    except json.JSONDecodeError:
        return jsonify({"status": "error", "message": "AI returned invalid JSON", "raw_response": response, "session_id": chat_session_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "raw_response": response, "session_id": chat_session_id})

@chat_bp.route("/save-message", methods=["POST"])
def save_message_route():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    chat_session_id = data.get("session_id")
    role = data.get("role")
    content = data.get("content")

    if not chat_session_id or not role or content is None:
        return jsonify({"status": "error", "message": "Missing fields"})

    save_chat_message(chat_session_id, session["user_id"], role, content)
    return jsonify({"status": "success"})

@chat_bp.route("/chat-sessions")
def chat_sessions():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, title, created_at, updated_at FROM chat_sessions
    WHERE user_id=%s ORDER BY updated_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    data = [{"id": r[0], "title": r[1] or "New chat", "created_at": str(r[2]), "updated_at": str(r[3])} for r in rows]
    return jsonify(data)

@chat_bp.route("/chat-session/<int:chat_session_id>/messages")
def chat_session_messages(chat_session_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT role, content, created_at FROM chat_messages
    WHERE session_id=%s AND user_id=%s ORDER BY id ASC
    """, (chat_session_id, user_id))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    data = [{"role": r[0], "content": r[1], "created_at": str(r[2])} for r in rows]
    return jsonify(data)