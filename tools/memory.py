import json

def save_history(task):
	with open("memory/history.json", "r") as file:
		history = json.load(file)
	
	history.append(task)
	
	with open("memory/history.json", "w") as file:
		json.dump(history, file, indent=4)
