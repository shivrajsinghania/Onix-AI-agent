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
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS task_results CASCADE;")
    cur.execute("DROP TABLE IF EXISTS workflows CASCADE;")
    cur.execute("DROP TABLE IF EXISTS task_queue CASCADE;")
    cur.execute("DROP TABLE IF EXISTS history CASCADE;")
    cur.execute("DROP TABLE IF EXISTS users CASCADE;")
    
    conn.commit()
    
    print("All tables deleted")
    
    cursor.close()
    conn.close()
