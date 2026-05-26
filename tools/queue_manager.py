import json

from datetime import datetime

from config.database import get_connection


MAX_RETRIES = 3


def add_task(task):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

    INSERT INTO task_queue (

        task_json,
        status,
        attempts

    )

    VALUES (%s, %s, %s)

    """, (

        json.dumps(task),
        "pending",
        0

    ))

    conn.commit()

    cursor.close()

    conn.close()


def get_pending_tasks():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

    SELECT *

    FROM task_queue

    WHERE status = 'pending'

    ORDER BY id ASC

    """)

    rows = cursor.fetchall()

    cursor.close()

    conn.close()

    pending = []

    for row in rows:

        pending.append((

            row[0],

            {

                "task": row[1],
                "status": row[2],
                "attempts": row[3],
                "error": row[4]

            }

        ))

    return pending


def mark_running(task_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

    UPDATE task_queue

    SET

        status = %s,
        started_at = %s

    WHERE id = %s

    """, (

        "running",
        datetime.now(),
        task_id

    ))

    conn.commit()

    cursor.close()

    conn.close()


def mark_completed(task_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

    UPDATE task_queue

    SET

        status = %s,
        completed_at = %s

    WHERE id = %s

    """, (

        "completed",
        datetime.now(),
        task_id

    ))

    conn.commit()

    cursor.close()

    conn.close()


def mark_failed(task_id, error):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

    UPDATE task_queue

    SET

        status = %s,
        error = %s,
        attempts = attempts + 1

    WHERE id = %s

    """, (

        "failed",
        str(error),
        task_id

    ))

    conn.commit()

    cursor.close()

    conn.close()


def retry_task(task_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

    SELECT attempts

    FROM task_queue

    WHERE id = %s

    """, (

        task_id,

    ))

    attempts = cursor.fetchone()[0]

    if attempts < MAX_RETRIES:

        cursor.execute("""

        UPDATE task_queue

        SET status = %s

        WHERE id = %s

        """, (

            "pending",
            task_id

        ))

    else:

        cursor.execute("""

        UPDATE task_queue

        SET status = %s

        WHERE id = %s

        """, (

            "permanently_failed",
            task_id

        ))

    conn.commit()

    cursor.close()

    conn.close()