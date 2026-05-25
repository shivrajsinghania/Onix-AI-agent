from config.database import get_connection

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

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

""")

# TASK QUEUE

cursor.execute("""

CREATE TABLE IF NOT EXISTS task_queue (

    id SERIAL PRIMARY KEY,

    task_json JSONB,

    status TEXT,
    attempts INTEGER,
    error TEXT,

    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    duration FLOAT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

""")

# WORKFLOWS

cursor.execute("""

CREATE TABLE IF NOT EXISTS workflows (

    id SERIAL PRIMARY KEY,

    workflow_json JSONB,

    status TEXT,

    current_step INTEGER,

    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    duration FLOAT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

""")

conn.commit()

cursor.close()

conn.close()

print("Database setup complete")