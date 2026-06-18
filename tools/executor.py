from tools.search import search
from tools.browser_actions import open_website
from tools.research import research_service

def execute_task(task):

    action = task["action"]

    result = None

    if action == "open_website":
        result = open_website(task["url"])

    elif action == "search":
        result = search(
            task["app"],
            task["query"]
        )

    elif action == "research_service":
        result = research_service(
            task["service"],
            task["state"]
        )

    return {
        "status": "completed",
        "result": result
    }