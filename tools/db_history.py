from config.database import get_connection

def save_history(task):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

    INSERT INTO history (
        action,
        app,
        target,
        message,
        query
    )

    VALUES (%s, %s, %s, %s, %s)

    """, (

        task.get("action"),
        task.get("app"),
        task.get("target"),
        task.get("message"),
        task.get("query")
    ))

    conn.commit()

    cursor.close()

    conn.close()