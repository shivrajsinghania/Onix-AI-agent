from tools.tool_definitions import TOOLS

def validate_task(task):
    action = task.get("action")

    if action not in TOOLS:
        return False, f"Unsupported action: {action}"

    tool = TOOLS[action]

    # research_service doesn't use an app field
    if action != "research_service":
        app = task.get("app")
        if app not in tool["apps"]:
            return False, f"Invalid app '{app}' for action '{action}'"

    for field in tool["required_fields"]:
        if field not in task:
            return False, f"Missing required field: {field}"

    return True, "Valid task"
