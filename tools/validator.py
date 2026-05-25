from tools.tool_definitions import TOOLS

def validate_task(task):

    action = task.get("action")

    if action not in TOOLS:

        return False, "Invalid action"

    tool = TOOLS[action]

    app = task.get("app")

    if app not in tool["apps"]:

        return False, "Invalid app"

    required_fields = tool["required_fields"]

    for field in required_fields:

        if field not in task:
            return False, f"Missing field: {field}"

    return True, "Valid task"
