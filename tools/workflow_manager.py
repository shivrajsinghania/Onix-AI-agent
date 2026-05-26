from config.database import get_connection
import json
from datetime import datetime


def create_workflow(tasks):

    conn = get_connection()

    cursor = conn.cursor()

    workflow_data = json.dumps(tasks)

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

        workflow_data,
        "running",
        0,
        datetime.now()

    ))

    workflow_id = cursor.fetchone()[0]

    conn.commit()

    cursor.close()

    conn.close()

    return {

        "id": workflow_id,
        "tasks": tasks
    }


def update_step(workflow_id, step):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

    UPDATE workflows

    SET current_step = %s

    WHERE id = %s

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

        status = %s,
        completed_at = %s

    WHERE id = %s

    """, (

        "completed",
        datetime.now(),
        workflow_id

    ))

    conn.commit()

    cursor.close()

    conn.close()