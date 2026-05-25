import json

MAX_RETRIES = 3

QUEUE_FILE = "memory/task_queue.json"


def load_queue():

    with open(QUEUE_FILE, "r") as file:

        return json.load(file)


def save_queue(queue):

    with open(QUEUE_FILE, "w") as file:

        json.dump(queue, file, indent=4)


def add_task(task):

    queue = load_queue()

    queue.append({

        "task": task,

        "status": "pending",

        "attempts": 0,

        "error": None
    })

    save_queue(queue)


def get_pending_tasks():

    queue = load_queue()

    pending = []

    for index, item in enumerate(queue):

        if item["status"] == "pending":

            pending.append((index, item))

    return pending


def mark_running(index):

    queue = load_queue()

    queue[index]["status"] = "running"

    save_queue(queue)


def mark_completed(index):

    queue = load_queue()

    queue[index]["status"] = "completed"

    save_queue(queue)


def mark_failed(index, error):

    queue = load_queue()

    queue[index]["status"] = "failed"

    queue[index]["error"] = str(error)

    queue[index]["attempts"] += 1

    save_queue(queue)


def retry_task(index):

    queue = load_queue()

    task = queue[index]

    if task["attempts"] < MAX_RETRIES:

        task["status"] = "pending"

    else:

        task["status"] = "permanently_failed"

    save_queue(queue)
