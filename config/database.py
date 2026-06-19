import os
import psycopg2

# ================== PATH SETUP ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_URL = os.environ.get("DATABASE_URL")

# ================== DATABASE ==================

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    #USERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
    id SERIAL PRIMARY KEY,
    email TEXT,
    username TEXT UNIQUE,
    password TEXT
    )
    """)
    
    # HISTORY
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history(
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action TEXT,
    app TEXT,
    target TEXT,
    message TEXT,
    query TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # TASK QUEUE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_queue(
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    task_json TEXT,
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
    CREATE TABLE IF NOT EXISTS workflows(
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    workflow_json TEXT,
    status TEXT,
    current_step INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    #Results table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_results(
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    task_id INTEGER,
    action TEXT,
    result_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # CHAT SESSIONS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions(
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # CHAT MESSAGES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages(
    id SERIAL PRIMARY KEY,
    session_id INTEGER,
    user_id INTEGER,
    role TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()