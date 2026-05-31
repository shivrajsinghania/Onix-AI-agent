def execute_task(task):
	action = task["action"]
	
	if action == "open website":
		open_website(task["url"])
		
	elif action == "search":
		search(
		task["app"],
		task["query"]
		)
	
	elif action == "send message":
		send_message(
		task["target"],
		task["message"]
		)
	
	return {"status": "completed"}