"""NeonDB schema initialization for structured memory storage."""

import os
import sys
from pathlib import Path

import yaml
from psycopg2 import pool

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

os.chdir(Path(__file__).resolve().parent.parent.parent.parent)


def get_driver():
    """Get NeonDB driver instance."""
    config_path = ".fleet/context/.neon/config.yaml"
    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found at {config_path}")
        return None

    with open(config_path) as f:
        config = yaml.safe_load(f)

    cloud_config = config.get("cloud", {})
    pooling_config = config.get("pooling", {})

    try:
        conn_pool = pool.ThreadedConnectionPool(
            minconn=pooling_config.get("min_size", 2),
            maxconn=pooling_config.get("max_size", 10),
            host=cloud_config.get("host"),
            database=cloud_config.get("database"),
            user=cloud_config.get("user"),
            password=cloud_config.get("password"),
            sslmode="require",
        )
        print(f"Connected to NeonDB (Host: {cloud_config.get('host')})")
        return conn_pool
    except Exception as e:
        print(f"Failed to connect to NeonDB: {e}")
        return None


def init_schema():
    """Initialize all tables for structured memory storage."""
    pool_conn = get_driver()
    if not pool_conn:
        return False

    schema_statements = [
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) UNIQUE NOT NULL,
            user_id VARCHAR(255),
            started_at TIMESTAMP DEFAULT NOW(),
            last_activity TIMESTAMP DEFAULT NOW(),
            metadata JSONB DEFAULT '{}',
            status VARCHAR(50) DEFAULT 'active',
            agent_context JSONB DEFAULT '[]'
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) REFERENCES sessions(session_id),
            role VARCHAR(50) NOT NULL,
            content TEXT,
            timestamp TIMESTAMP DEFAULT NOW(),
            metadata JSONB DEFAULT '{}',
            embedding_id VARCHAR(255)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255),
            preferences JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            last_login TIMESTAMP,
            total_sessions INTEGER DEFAULT 0,
            total_messages INTEGER DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_states (
            id SERIAL PRIMARY KEY,
            agent_id VARCHAR(255) UNIQUE NOT NULL,
            agent_name VARCHAR(255) NOT NULL,
            config JSONB DEFAULT '{}',
            state JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            total_runs INTEGER DEFAULT 0,
            total_tasks INTEGER DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS analytics (
            id SERIAL PRIMARY KEY,
            date DATE DEFAULT CURRENT_DATE,
            metric_type VARCHAR(100) NOT NULL,
            metric_value FLOAT NOT NULL,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(date, metric_type)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS skills (
            id SERIAL PRIMARY KEY,
            skill_name VARCHAR(255) UNIQUE NOT NULL,
            category VARCHAR(100),
            description TEXT,
            implementation TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            usage_count INTEGER DEFAULT 0,
            success_rate FLOAT DEFAULT 0.0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS workflows (
            id SERIAL PRIMARY KEY,
            workflow_id VARCHAR(255) UNIQUE NOT NULL,
            workflow_type VARCHAR(100),
            status VARCHAR(50) DEFAULT 'pending',
            input_data JSONB DEFAULT '{}',
            output_data JSONB DEFAULT '{}',
            started_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP,
            duration_ms INTEGER,
            metadata JSONB DEFAULT '{}'
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)",
        "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_analytics_date ON analytics(date)",
        "CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category)",
        "CREATE INDEX IF NOT EXISTS idx_workflows_type ON workflows(workflow_type)",
    ]

    for i, statement in enumerate(schema_statements):
        try:
            conn = pool_conn.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(statement)
                conn.commit()
                print(f"  Statement {i + 1}/{len(schema_statements)}")
            finally:
                pool_conn.putconn(conn)
        except Exception as e:
            print(f"  Statement {i + 1} failed: {e}")
            pool_conn.closeall()
            return False

    pool_conn.closeall()
    print("\nSchema initialization complete")
    return True


def drop_schema():
    """Drop all tables."""
    pool_conn = get_driver()
    if not pool_conn:
        return False

    tables = [
        "workflows",
        "skills",
        "analytics",
        "agent_states",
        "users",
        "messages",
        "sessions",
    ]

    for table in tables:
        try:
            conn = pool_conn.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                conn.commit()
                print(f"  Dropped: {table}")
            finally:
                pool_conn.putconn(conn)
        except Exception as e:
            print(f"  Failed to drop {table}: {e}")
            pool_conn.closeall()
            return False

    pool_conn.closeall()
    print("\nSchema dropped")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "drop":
        drop_schema()
    else:
        init_schema()
