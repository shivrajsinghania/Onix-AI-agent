import json

WORKFLOW_FILE = "memory/workflows.json"

def load_workflows():
	with open(WORKFLOW_FILE, "r") as file:
		return json.load(file)
		
def save_workflows(workflows):
	with open(WORKFLOW_FILE, "w") as file:
		json.dump(workflows, file, indent=4)
		
def create_workflow(tasks):
	workflows = load_workflows()
	workflow = {
	"id": len(workflows) + 1,
	"status": "running",
	"current_step": 0,
	"tasks": tasks
	}
	workflows.append(workflow)
	save_workflows(workflows)
	return workflow
	
def update_step(workflow_id, step):
    
    workflows = load_workflows()
    
    for workflow in workflows:
        
        if workflow["id"] == workflow_id:
            workflow["current_step"] = step

    save_workflows(workflows)
    
def complete_workflow(workflow_id):
    workflows = load_workflows()

    for workflow in workflows:
        if workflow["id"] == workflow_id:
            workflow["status"] = "completed"

    save_workflows(workflows)
