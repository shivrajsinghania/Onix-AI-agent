import os
import psycopg2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL, connect_timeout=10)

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_queue (
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workflows (
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_results (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        task_id INTEGER,
        action TEXT,
        result_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        title TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id SERIAL PRIMARY KEY,
        session_id INTEGER,
        user_id INTEGER,
        role TEXT,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS service_knowledge (
        id SERIAL PRIMARY KEY,
        service_key TEXT NOT NULL UNIQUE,
        service_name TEXT NOT NULL,
        state TEXT NOT NULL,
        jurisdiction_type TEXT NOT NULL DEFAULT 'state',
        category TEXT,
        icon TEXT,
        department TEXT,
        portal_name TEXT,
        portal_url TEXT,
        apply_url TEXT,
        documents_json TEXT DEFAULT '[]',
        eligibility TEXT,
        fees TEXT,
        timeline TEXT,
        photo_size TEXT,
        signature_size TEXT,
        upload_limits TEXT,
        validity TEXT,
        application_steps_json TEXT DEFAULT '[]',
        notes TEXT,
        sources_json TEXT DEFAULT '[]',
        confidence_score INTEGER DEFAULT 0,
        last_verified TEXT,
        manual_review_needed INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1,
        version INTEGER DEFAULT 1,
        updated_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS service_versions (
        id SERIAL PRIMARY KEY,
        service_key TEXT NOT NULL,
        version INTEGER NOT NULL,
        snapshot_json TEXT NOT NULL,
        change_summary TEXT,
        changed_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS service_variants (
        id SERIAL PRIMARY KEY,
        parent_service_key TEXT NOT NULL,
        parent_variant_id INTEGER,
        variant_key TEXT NOT NULL,
        label TEXT NOT NULL,
        icon TEXT,
        department TEXT,
        portal_name TEXT,
        portal_url TEXT,
        apply_url TEXT,
        documents_json TEXT,
        eligibility TEXT,
        fees TEXT,
        timeline TEXT,
        photo_size TEXT,
        signature_size TEXT,
        upload_limits TEXT,
        validity TEXT,
        application_steps_json TEXT,
        notes TEXT,
        sources_json TEXT,
        sort_order INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_service_key) REFERENCES service_knowledge(service_key),
        FOREIGN KEY (parent_variant_id) REFERENCES service_variants(id)
    )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_variants_service ON service_variants(parent_service_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_variants_parent ON service_variants(parent_variant_id)")

    conn.commit()
    print("tables created")
    cursor.close()
    conn.close()
