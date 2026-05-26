import json

from flask import Flask, request, jsonify, render_template

from tools.ai import ask_ai
from tools.whatsapp import send_message
from tools.db_history import save_history
from tools.search import search
from tools.validator import validate_task
from tools.queue_manager import (add_task, get_pending_tasks, mark_completed, mark_running, mark_failed, retry_task)
from tools.workflow_manager import (create_workflow, update_step, complete_workflow)
from tools.context_manager import (store_step_output, get_step_output)
from tools.observer import observe_website
from tools.browser_actions import (open_website, click_element, type_text, submit_form)
from config.database import get_connection
from config.database import init_db

app = Flask(__name__)
init_db()


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
        workflow = create_workflow(tasks)
        
        for step, task in enumerate(workflow["tasks"]):
        	update_step(workflow["id"], step)
        	task["step"] = step
        	add_task(task)
        
        pending_tasks = get_pending_tasks()
        for index, item in pending_tasks:
        	
        	task = item["task"]
        	step = task["step"]
        	action = task["action"]
        	
        	is_valid, reason = validate_task(task)
        	if not is_valid:
        		print(f"Task rejected: {reason}")
        		continue
        	try:
        		mark_running(index)
        		
        		if action == "send_message":
        			target = task["target"]
        			message = task["message"]
        			send_message(target, message)
        			store_step_output(workflow["id"], step, f"sent message to {target}" )
        			
        		elif action == "search":
        			app_name = task["app"]
        			query = task["query"]
        			search(app_name, query)
        			store_step_output(workflow["id"], step, f"Searched {query} on {app_name}" )
        		
        		elif action == "observe_website":
        			url = task["url"]
        			observation = observe_website(url)
        			print(observation)
        			store_step_output(workflow["id"], step, observation)
        			
        		elif action == "open_website":
        			url = task["url"]
        			open_website(url)
        			store_step_output(workflow["id"], step, f"Opened {url}")
        			
        		elif action == "click_element":
        			element = task["element"]
        			click_element(element)
        			store_step_output(workflow["id"], step, f"Clicked {element}")
        			
        		elif action == "type_text":
        			text = task["text"]
        			type_text(text)
        			store_step_output(workflow["id"], step, f"Typed {text}")
        			
        		elif action == "submit_form":
        			submit_form()
        			store_step_output(workflow["id"], step, "Submitted form")
        		
        		save_history(task)
        		mark_completed(index)
        		complete_workflow(workflow["id"])
        	
        	except Exception as e:
        		mark_failed(index, e)
        		retry_task(index)
        		print(f"Execution failed: {e}")
        		
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

    SELECT *

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
            "created_at": str(row[6])

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
            "task": row[1],
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
            "workflow": row[1],
            "status": row[2],
            "current_step": row[3],
            "started_at": str(row[4]),
            "completed_at": str(row[5]),
            "duration": row[6],
            "created_at": str(row[7])

        })

    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
