import json

CONTEXT_FILE = "memory/workflow_context.json"


def load_context():

    with open(CONTEXT_FILE, "r") as file:

        return json.load(file)


def save_context(context):

    with open(CONTEXT_FILE, "w") as file:

        json.dump(context, file, indent=4)


def store_step_output(workflow_id, step, output):

    context = load_context()

    workflow_key = str(workflow_id)

    if workflow_key not in context:

        context[workflow_key] = {}

    context[workflow_key][str(step)] = output

    save_context(context)


def get_step_output(workflow_id, step):

    context = load_context()

    workflow_key = str(workflow_id)

    return context.get(workflow_key, {}).get(str(step))
