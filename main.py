import json
from flask import Flask, request, jsonify, render_template
from datetime import datetime
from tools.ai import ask_ai
from tools.whatsapp import send_message
from tools.search import search
from tools.validator import validate_task
from tools.observer import observe_website
from tools.browser_actions import (open_website, click_element, type_text, submit_form)
from config.database import get_connection
from config.database import create_tables

app = Flask(__name__)

create_tables()

def save_history(task, status):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

    INSERT INTO history (
        action,
        app,
        target,
        message,
        query,
        status
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    """, (
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

def create_workflow(tasks):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO workflows (
        workflow_json,
        status,
        current_step,
        started_at
    )
    VALUES (%s, %s, %s, %s)
    RETURNING id
    """, (

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

def add_task(task):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO task_queue (
        task_json,
        status,
        attempts
    )
    VALUES (%s, %s, %s)
    RETURNING id
    """, (
        json.dumps(task),
        "pending",
        0
    ))
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



@app.route("/")
def home():
    return render_template("agent.html")

@app.route("/ask", methods=["POST"])

def ask():

    user_data = request.get_json()
    question = user_data["message"]
    response = ask_ai(question)

    try:

        workflow_data = json.loads(response)
        tasks = workflow_data["workflow"]
        workflow_id = create_workflow(tasks)
        
        for step, task in enumerate(tasks):
        	update_workflow_step(workflow_id, step)
        	action = task["action"]
        	is_valid, reason = validate_task(task)
        	if not is_valid:
        		print(f"Task rejected: {reason}")
        		continue
        	task_id = add_task(task)
        	
        	try:
        		mark_running(task_id)
        		if action == "send_message":
        			target = task["target"]
        			message = task["message"]
        			send_message(target, message)
        			
        		elif action == "search":
        			app_name = task["app"]
        			query = task["query"]
        			search(app_name, query)
        		
        		elif action == "observe_website":
        			url = task["url"]
        			observation = observe_website(url)
        			print(observation)
        			
        		elif action == "open_website":
        			url = task["url"]
        			open_website(url)
        		
        		elif action == "click_element":
        			element = task["element"]
        			click_element(element)
        			
        		elif action == "type_text":
        			text = task["text"]
        			type_text(text)
        			
        		elif action == "submit_form":
        			submit_form()
        			
        		save_history(task, "completed")
        		mark_completed(task_id)
        		
        	except Exception as e:
        		mark_failed(task_id, e)
        		save_history(task, "failed")
        		print(f"Execution failed: {e}")
        		
        complete_workflow(workflow_id)
        	
        return jsonify({
            "status": "success",
            "tasks": tasks
        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e),
            "raw_response": response
        })


@app.route("/history")
def history():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        id,
        action,
        app,
        target,
        message,
        query,
        status,
        created_at
    FROM history
    ORDER BY id DESC
    """)

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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM task_queue
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    data = []

    for row in rows:
        data.append({
            "id": row[0],
            "task": json.loads(row[1]),
            "status": row[2],
            "attempts": row[3],
            "error": row[4],
            "started_at": str(row[5]),
            "completed_at": str(row[6]),
            "created_at": str(row[7])
        })

    return jsonify(data)
	
@app.route("/workflows")
def workflows():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM workflows
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    data = []

    for row in rows:
        data.append({
            "id": row[0],
            "workflow": json.loads(row[1]),
            "status": row[2],
            "current_step": row[3],
            "started_at": str(row[4]),
            "completed_at": str(row[5]),
            "created_at": str(row[6])
        })

    return jsonify(data)

@app.route("/delete/<table>/<int:item_id>", methods=["DELETE"])
def delete_item(table, item_id):
	allowed_tables = ["history", "queue", "workflow"]
	
	if table not in allowed_tables:
		return jsonify({
		"status": "error",
		"message": "Invalid table"
		})
		
	table_mapping = {
	"history": "history",
	"queue": "task_queue",
	"workflow": "workflows"
	}
	
	real_table = table_mapping[table]
	
	conn = get_connection()
	cursor = conn.cursor()
	
	query = f"DELETE FROM {real_table} WHERE id=%s"
	
	cursor.execute(query, (item_id, ))
	
	conn.commit()
	cursor.close()
	conn.close()
	
	return jsonify({
	"status": "success "
	})

@app.route("/clear/<table>", methods=["DELETE"])
def clear_table(table):
	allowed_tables = ["history", "queue", "workflow"]
	
	if table not in allowed_tables:
		return jsonify({
		"status": "error",
		"message": "Invalid table"
		})
		
	table_mapping = {
	"history": "history",
	"queue": "task_queue",
	"workflow": "workflows"
	}
	
	real_table = table_mapping[table]
	
	conn = get_connection()
	cursor = conn.cursor()
	
	query = f"DELETE FROM {real_table}"
	
	cursor.execute(query)
	
	conn.commit()
	cursor.close()
	conn.close()
	
	return jsonify({
	"status": "success"
	})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)