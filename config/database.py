import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():

    return psycopg2.connect(DATABASE_URL)


def create_tables():

    conn = get_connection()

    cursor = conn.cursor()

    # HISTORY

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS history (

        id SERIAL PRIMARY KEY,

        action TEXT,
        app TEXT,
        target TEXT,
        message TEXT,
        query TEXT,
        status TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )

    """)
    
    cursor.execute("""
    ALTER TABLE history
    ADD COLUMN IF NOT EXISTS status TEXT
    """)

    # TASK QUEUE

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS task_queue (

        id SERIAL PRIMARY KEY,

        task_json JSONB,

        status TEXT,
        attempts INTEGER DEFAULT 0,
        error TEXT,

        started_at TIMESTAMP,
        completed_at TIMESTAMP,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )

    """)

    # WORKFLOWS

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS workflows (

        id SERIAL PRIMARY KEY,

        workflow_json JSONB,

        status TEXT,
        current_step INTEGER DEFAULT 0,

        started_at TIMESTAMP,
        completed_at TIMESTAMP,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )

    """)

    conn.commit()

    cursor.close()
    conn.close()