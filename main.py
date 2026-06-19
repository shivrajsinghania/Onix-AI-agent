import json
import psycopg2
from flask import Flask, request, jsonify, render_template, redirect, session, flash, make_response
from datetime import datetime
from tools.ai import ask_ai
from tools.search import search
from tools.validator import validate_task
from tools.observer import observe_website
from tools.analyzer import analyze_observation
from tools.research import research_service
from tools.browser_actions import (open_website, click_element, type_text, submit_form)
from tools.executor import execute_task
from config.database import (get_connection, create_tables, DATABASE_URL)
from werkzeug.security import generate_password_hash, check_password_hash

# ================== APP ==================
app = Flask(__name__)
app.secret_key = "mysecretkey"

create_tables()

@app.after_request
def add_no_cache_headers(response):
    # Prevent bfcache on auth-sensitive pages
    if request.path in ["/agent", "/login-page", "/", "/signup"]:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# ================== FUNCTIONS ==================

def add_user(email, username, hashed_password):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO users(email, username, password)
            VALUES(%s, %s, %s)
            """,
                (email, username, hashed_password)
            )
            conn.commit()
            
        return "success"
        
    except Exception as e:
        print(e)
        return "exists"

def validate_user(username, password):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()

        if user:
            stored_hash = user[3]
            return check_password_hash(stored_hash, password)
        return False

def save_history(user_id, task, status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO history(
    user_id, action, app, target, message, query, status
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
    user_id,
    task.get("action"),
    task.get("app"),
    task.get("target"),
    task.get("message"),
    task.get("query"),
    status
    ))

    conn.commit()
    cursor.close()
    conn.close()

def save_result(user_id, task_id, action, result):
	conn = get_connection()
	cursor = conn.cursor()
	
	cursor.execute("""
	INSERT INTO task_results(
	user_id, task_id, action, result_json
	)
	VALUES(%s, %s, %s, %s)
	""", (user_id, task_id, action, json.dumps(result)
	))
	
	conn.commit()
	cursor.close()
	conn.close()

def create_chat_session(user_id, title):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO chat_sessions(user_id, title)
    VALUES (%s, %s)
    RETURNING id
    """, (user_id, title))

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

    cursor.execute("""
    UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=%s
    """, (session_id,))

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
    INSERT INTO workflows (
    user_id, workflow_json, status, current_step, started_at
    )
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id
    """, (
    user_id,
    json.dumps(tasks),
    "running",
    0,
    datetime.now()
    ))

    workflow_id = cursor.fetchone()[0]
    
    conn.commit()
    cursor.close()
    conn.close()

    return workflow_id

def update_workflow_step(workflow_id, step):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE workflows
    SET current_step=%s
    WHERE id=%s
    """, (
        step,
        workflow_id
    ))

    conn.commit()
    cursor.close()
    conn.close()

def complete_workflow(workflow_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE workflows
    SET
        status=%s,
        completed_at=%s
    WHERE id=%s
    """, (
        "completed",
        datetime.now(),
        workflow_id
    ))

    conn.commit()
    cursor.close()
    conn.close()

def add_task(user_id, task):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO task_queue(
    user_id, task_json, status, attempts
    )
    VALUES (%s, %s, %s, %s)
    RETURNING id
    """, (
    user_id, json.dumps(task), "pending", 0))
    
    task_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()
    
    return task_id

def mark_running(task_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE task_queue
    SET
        status=%s,
        started_at=%s
    WHERE id=%s
    """, (
        "running",
        datetime.now(),
        task_id
    ))

    conn.commit()
    cursor.close()
    conn.close()

def mark_completed(task_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE task_queue
    SET
        status=%s,
        completed_at=%s
    WHERE id=%s
    """, (
        "completed",
        datetime.now(),
        task_id
    ))

    conn.commit()
    cursor.close()
    conn.close()

def mark_failed(task_id, error):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE task_queue
    SET
        status=%s,
        error=%s,
        attempts=attempts+1
    WHERE id=%s
    """, (
        "failed",
        str(error),
        task_id
    ))

    conn.commit()
    cursor.close()
    conn.close()

# ================== ROUTES ==================
@app.route("/")
def welcome():
    if "user" in session:
    	return redirect("/agent")
    	
    return render_template("landing_page_onix.html")

@app.route("/signup")
def signup():
    return render_template("signup_onix.html")

@app.route("/submit", methods=["POST"])
def submit():
    email = request.form.get("email")
    username = request.form.get("username")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if not email or "@" not in email:
        flash("Please enter a valid email!", "error")
        return render_template("signup_onix.html", old=request.form)

    if not username:
        flash("Please create a valid username!", "error")
        return render_template("signup_onix.html", old=request.form)

    if len(password) < 6:
        flash("Password must be at least 6 characters!", "error")
        return render_template("signup_onix.html", old=request.form)

    if password != confirm_password:
        flash("Passwords do not match!", "error")
        return render_template("signup_onix.html", old=request.form)

    hashed_password = generate_password_hash(password)
    result = add_user(email, username, hashed_password)

    if result == "success":
        with get_connection() as conn:
        	cursor = conn.cursor()
        	
        	cursor.execute("SELECT id FROM users WHERE username=%s", (username, ))
        	user = cursor.fetchone()
        
        session["user"] = username
        session["user_id"] = user[0]
        
        return redirect("/agent")

    flash("Username already exists!", "error")
    return redirect("/signup")

@app.route("/login-page")
def loginpage():
    if "user" in session:
    	return redirect("/agent")
    	
    return render_template("login_onix.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        flash("Please enter username and password!", "error")
        return redirect("/login-page")

    if validate_user(username, password):
        with get_connection() as conn:
        	cursor = conn.cursor()
        	
        	cursor.execute("SELECT id FROM users WHERE username=%s", (username, ))
        	user = cursor.fetchone()
        	
        session["user"] = username
        session["user_id"] = user[0]
        
        return redirect("/agent")

    flash("Invalid login credentials!", "error")
    return redirect("/login-page")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/check-session")
def check_session():
	if "user" in session:
		return jsonify({"logged_in": True})
	return jsonify({"logged_in": False})

@app.route("/agent")
def home():
	if "user" not in session:
		return redirect("/login-page")
		
	return render_template("agent.html")

@app.route("/ask", methods=["POST"])
def ask():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_data = request.get_json() or {}
    question = user_data.get("message")
    if not question:
    	return jsonify({
    	"error": "Message required"
    	}), 400
    history = user_data.get("history", [])[-15:]
    user_context = user_data.get("user_context", {})
    user_id = session["user_id"]

    # ── Chat session tracking ──
    chat_session_id = user_data.get("session_id")
    if not chat_session_id:
        raw_title = (question or "New chat").strip()
        title = raw_title[:50] + ("…" if len(raw_title) > 50 else "")
        chat_session_id = create_chat_session(user_id, title)
    save_chat_message(chat_session_id, user_id, "user", question)

    response = ask_ai(question, history=history, user_context=user_context)

    try:
        workflow_data = json.loads(response)

        # Handle normal conversation (greetings, questions about Onix, etc.)
        if workflow_data.get("status") == "conversation":
        	ai_message = workflow_data.get(
        	"message",
        	"How can I help you?"
        	)
        	save_chat_message(
        	chat_session_id,
        	user_id,
        	"assistant",
        	ai_message
        	)
        	
        	return jsonify({
        	"status": "conversation",
        	"message": ai_message,
        	"session_id": chat_session_id
        	})

        # Handle clarification needed
        if workflow_data.get("status") == "need_clarification":
            
            save_chat_message(
            chat_session_id,
            user_id,
            "assistant",
            workflow_data["question"]
            )
            
            return jsonify({
                "status": "need_clarification",
                "question": workflow_data["question"],
                "session_id": chat_session_id
            })

        # Handle unsupported request
        if workflow_data.get("status") == "unsupported":
            
            save_chat_message(
            chat_session_id,
            user_id,
            "assistant",
            workflow_data.get("message", "")
            )
            
            return jsonify({
                "status": "unsupported",
                "message": workflow_data.get("message", "This request is not supported."),
                "session_id": chat_session_id
            })

        # Handle normal workflow
        tasks = workflow_data["workflow"]

        user_id = session["user_id"]
        workflow_id = create_workflow(user_id, tasks)

        # Collect results to return to frontend
        research_results = []
        observe_results = []

        for step, task in enumerate(tasks):

            update_workflow_step(workflow_id, step)

            action = task["action"]

            is_valid, reason = validate_task(task)

            if not is_valid:
                print(f"Task rejected: {reason}")
                continue

            task_id = add_task(user_id, task)

            try:
                mark_running(task_id)

                if action == "research_service":
                    subtype = task.get("subtype")  # optional, set after user picks
                    result = research_service(task["service"], task["state"], subtype=subtype)
                    save_result(user_id, task_id, "research", result)
                    research_results.append(result)

                elif action == "search":
                    app_name = task["app"]
                    query = task["query"]
                    search(app_name, query)

                elif action == "observe_website":
                    url = task["url"]
                    observation = observe_website(url)
                    save_result(user_id, task_id, action, observation)
                    analysis = analyze_observation(observation)
                    save_result(user_id, task_id, "analysis", {"analysis": analysis})
                    observe_results.append({
                        "url": url,
                        "title": observation.get("title", ""),
                        "content": observation.get("content", "")[:800],
                        "analysis": analysis
                    })

                elif action == "open_website":
                    open_website(task["url"])

                elif action == "click_element":
                    click_element(task["element"])

                elif action == "type_text":
                    type_text(task["text"])

                elif action == "submit_form":
                    submit_form()

                save_history(user_id, task, "completed")
                mark_completed(task_id)

            except Exception as e:
                mark_failed(task_id, e)
                save_history(user_id, task, "failed")
                print(f"Execution failed: {e}")

        complete_workflow(workflow_id)

        # Return research result
        if research_results:
            r = research_results[0]

            # Service has subtypes — ask user to pick before spending SerpAPI credit
            if r.get("needs_subtype"):
                service_name = r.get("service_name", r["service"])
                save_chat_message(
                    chat_session_id,
                    user_id,
                    "assistant",
                    needs_subtype_summary_text(service_name, r["subtypes"])
                )
                return jsonify({
                    "status": "needs_subtype",
                    "service": r["service"],
                    "state": r["state"],
                    "service_name": service_name,
                    "subtypes": r["subtypes"],
                    "session_id": chat_session_id
                })

            full_response = {
                "status": "research",
                "tasks": tasks,
                "research": r,
                "remember": {"state": r.get("state", "")}
            }
            save_chat_message(
                chat_session_id,
                user_id,
                "assistant",
                "json:" + json.dumps(full_response)
            )
            return jsonify({**full_response, "session_id": chat_session_id})

        # Return observe result
        if observe_results:
            full_response = {
                "status": "observe",
                "tasks": tasks,
                "observation": observe_results[0]
            }
            save_chat_message(
                chat_session_id,
                user_id,
                "assistant",
                "json:" + json.dumps(full_response)
            )
            return jsonify({**full_response, "session_id": chat_session_id})

        full_response = {"status": "success", "tasks": tasks}
        save_chat_message(
            chat_session_id,
            user_id,
            "assistant",
            "json:" + json.dumps(full_response)
        )
        return jsonify({**full_response, "session_id": chat_session_id})

    except json.JSONDecodeError:
        return jsonify({
            "status": "error",
            "message": "AI returned invalid JSON",
            "raw_response": response,
            "session_id": chat_session_id
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "raw_response": response,
            "session_id": chat_session_id
        })

@app.route("/save-message", methods=["POST"])
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

@app.route("/chat-sessions")
def chat_sessions():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, title, created_at, updated_at
    FROM chat_sessions
    WHERE user_id=%s
    ORDER BY updated_at DESC
    """, (user_id,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    data = []
    for row in rows:
        data.append({
            "id": row[0],
            "title": row[1] or "New chat",
            "created_at": str(row[2]),
            "updated_at": str(row[3])
        })

    return jsonify(data)

@app.route("/chat-session/<int:chat_session_id>/messages")
def chat_session_messages(chat_session_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT role, content, created_at
    FROM chat_messages
    WHERE session_id=%s AND user_id=%s
    ORDER BY id ASC
    """, (chat_session_id, user_id))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    data = [{"role": r[0], "content": r[1], "created_at": str(r[2])} for r in rows]
    return jsonify(data)

@app.route("/history")
def history():
    if "user" not in session:
    	return jsonify({"error": "Unauthorized"}), 401
    	
    conn = get_connection()
    cursor = conn.cursor()
    
    user_id = session["user_id"]

    cursor.execute("""
    SELECT
    id, action, app, target, message, query, status, created_at
    FROM history
    WHERE user_id=%s
    ORDER BY id DESC
    """, (user_id, ))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    data = []

    for row in rows:

        data.append({
            "id": row[0],
            "action": row[1],
            "app": row[2],
            "target": row[3],
            "message": row[4],
            "query": row[5],
            "status": row[6],
            "created_at": str(row[7])
        })

    return jsonify(data)
	
@app.route("/queue")
def queue():
    if "user" not in session:
    	return jsonify({"error": "Unauthorized"}), 401
    	
    conn = get_connection()
    cursor = conn.cursor()
    
    user_id = session["user_id"]

    cursor.execute("""
    SELECT *
    FROM task_queue
    WHERE user_id=%s
    ORDER BY id DESC
    """, (user_id, ))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    data = []

    for row in rows:
        data.append({
        "id": row[0],
        "task": json.loads(row[2]),
        "status": row[3],
        "attempts": row[4],
        "error": row[5],
        "started_at": str(row[6]),
        "completed_at": str(row[7]),
        "created_at": str(row[8])
        })

    return jsonify(data)
	
@app.route("/workflows")
def workflows():
    if "user" not in session:
    	return jsonify({"error": "Unauthorized"}), 401
    	
    conn = get_connection()
    cursor = conn.cursor()
    
    user_id = session["user_id"]

    cursor.execute("""
    SELECT *
    FROM workflows
    WHERE user_id=%s
    ORDER BY id DESC
    """, (user_id, ))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    data = []

    for row in rows:
        data.append({
            "id": row[0],
            "workflow": json.loads(row[2]),
            "status": row[3],
            "current_step": row[4],
            "started_at": str(row[5]),
            "completed_at": str(row[6]),
            "created_at": str(row[7])            
        })

    return jsonify(data)

@app.route("/delete/<table>/<int:item_id>", methods=["DELETE"])
def delete_item(table, item_id):
	if "user" not in session:
	   return jsonify({"error": "Unauthorized"}), 401
	   
	allowed_tables = ["history", "queue", "workflow", "results"]
	
	if table not in allowed_tables:
		return jsonify({
		"status": "error",
		"message": "Invalid table"
		})
		
	table_mapping = {
	"history": "history",
	"queue": "task_queue",
	"workflow": "workflows",
	"results": "task_results"
	}
	
	real_table = table_mapping[table]
	
	conn = get_connection()
	cursor = conn.cursor()
	
	user_id = session["user_id"]
	
	query = f"DELETE FROM {real_table} WHERE id=%s AND user_id=%s"
	
	cursor.execute(query, (item_id, user_id))
	
	conn.commit()
	cursor.close()
	conn.close()
	
	return jsonify({
	"status": "success "
	})

@app.route("/clear/<table>", methods=["DELETE"])
def clear_table(table):
	if "user" not in session:
	   return jsonify({"error": "Unauthorized"}), 401
	
	allowed_tables = ["history", "queue", "workflow", "results"]
	
	if table not in allowed_tables:
		return jsonify({
		"status": "error",
		"message": "Invalid table"
		})
		
	table_mapping = {
	"history": "history",
	"queue": "task_queue",
	"workflow": "workflows",
	"results": "task_results"
	}
	
	real_table = table_mapping[table]
	
	conn = get_connection()
	cursor = conn.cursor()
	
	user_id = session["user_id"]
	
	query = f"""DELETE FROM {real_table} WHERE user_id=%s"""
	
	cursor.execute(query, (user_id, ))
	
	conn.commit()
	cursor.close()
	conn.close()
	
	return jsonify({
	"status": "success"
	})

@app.route("/results")
def results():
	if "user" not in session:
	   return jsonify({"error": "Unauthorized"}), 401
	   
	conn = get_connection()
	cursor = conn.cursor()
	
	user_id = session["user_id"]
	
	cursor.execute("""
	SELECT *
	FROM task_results
	WHERE user_id=%s
	ORDER BY id DESC
	""", (user_id, ))
	
	rows = cursor.fetchall()
	cursor.close()
	conn.close()
	
	data = []
	
	for row in rows:
		data.append({
		"id": row[0],
		"task_id": row[2],
		"action": row[3],
		"result": json.loads(row[4]),
		"created_at": str(row[5])
		})
		
	return jsonify(data)

@app.route("/research-subtype", methods=["POST"])
def research_subtype():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    service = data.get("service")
    state = data.get("state")
    subtype = data.get("subtype")
    subtype_label = data.get("subtype_label", subtype)
    chat_session_id = data.get("session_id")

    if not service or not state or not subtype:
        return jsonify({"status": "error", "message": "Missing service, state, or subtype"})

    user_id = session["user_id"]

    if chat_session_id:
        save_chat_message(chat_session_id, user_id, "user", subtype_label)

    try:
        result = research_service(service, state, subtype=subtype)
        task = {"action": "research_service", "service": service, "state": state, "subtype": subtype}
        task_id = add_task(user_id, task)
        mark_running(task_id)
        save_result(user_id, task_id, "research", result)
        save_history(user_id, task, "completed")
        mark_completed(task_id)

        if chat_session_id:
            full_response = {"status": "research", "research": result, "remember": {"state": state}}
            save_chat_message(chat_session_id, user_id, "assistant", "json:" + json.dumps(full_response))

        return jsonify({
            "status": "research",
            "research": result,
            "remember": {"state": state},
            "session_id": chat_session_id
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/execute", methods=["POST"])
def execute():
	if "user" not in session:
	   return jsonify({"error": "Unauthorized"}), 401
	   
	task = request.get_json()
	result = execute_task(task)
	return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)