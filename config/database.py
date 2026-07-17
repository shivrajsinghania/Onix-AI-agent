import os
import psycopg2

# ================== PATH SETUP ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_URL = os.environ.get("DATABASE_URL")

# ================== DATABASE ==================

def get_connection():
    return psycopg2.connect(DATABASE_URL, connect_timeout=10)

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS chat_messages CASCADE")
    cursor.execute("DROP TABLE IF EXISTS chat_sessions CASCADE")
    cursor.execute("DROP TABLE IF EXISTS task_results CASCADE")
    cursor.execute("DROP TABLE IF EXISTS task_queue CASCADE")
    cursor.execute("DROP TABLE IF EXISTS workflows CASCADE")
    cursor.execute("DROP TABLE IF EXISTS history CASCADE")
    cursor.execute("DROP TABLE IF EXISTS service_variants CASCADE")
    cursor.execute("DROP TABLE IF EXISTS service_versions CASCADE")
    cursor.execute("DROP TABLE IF EXISTS service_knowledge CASCADE")
    cursor.execute("DROP TABLE IF EXISTS users CASCADE")
        
    conn.commit()
    print("database deleted")
    cursor.close()
    conn.close()
