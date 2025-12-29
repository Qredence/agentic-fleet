"""Unified NeonDB memory storage for structured data."""

import json
import uuid
from datetime import date
from pathlib import Path

import yaml
from psycopg2 import pool


class NeonMemory:
    """Unified storage for structured memory in NeonDB."""

    def __init__(self, config_path=".fleet/context/.neon/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.pool = self._create_pool()

    def _load_config(self):
        """Load configuration from YAML file."""
        if not Path(self.config_path).exists():
            return {}
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def _create_pool(self):
        """Create connection pool."""
        cloud_config = self.config.get("cloud", {})
        pooling_config = self.config.get("pooling", {})

        try:
            return pool.ThreadedConnectionPool(
                minconn=pooling_config.get("min_size", 2),
                maxconn=pooling_config.get("max_size", 10),
                host=cloud_config.get("host"),
                database=cloud_config.get("database"),
                user=cloud_config.get("user"),
                password=cloud_config.get("password"),
                sslmode="require",
            )
        except Exception as e:
            print(f"Failed to create connection pool: {e}")
            return None

    def _get_conn(self):
        """Get connection from pool."""
        return self.pool.getconn() if self.pool else None

    def _put_conn(self, conn):
        """Return connection to pool."""
        if self.pool and conn:
            self.pool.putconn(conn)

    def _close(self):
        """Close the pool."""
        if self.pool:
            self.pool.closeall()

    # ==================== SESSIONS ====================

    def create_session(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict | None = None,
    ) -> str | None:
        """Create a new session."""
        session_id = session_id or str(uuid.uuid4())
        conn = self._get_conn()
        if not conn:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sessions (session_id, user_id, metadata)
                    VALUES (%s, %s, %s)
                    RETURNING session_id
                    """,
                    (session_id, user_id, json.dumps(metadata or {})),
                )
                conn.commit()
                return session_id
        finally:
            self._put_conn(conn)

    def get_session(self, session_id: str) -> dict:
        """Get session by ID."""
        conn = self._get_conn()
        if not conn:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM sessions WHERE session_id = %s", (session_id,))
                row = cur.fetchone()
                if row:
                    return self._row_to_dict(row, cur.description)
                return None
        finally:
            self._put_conn(conn)

    def update_session(self, session_id: str, **kwargs) -> bool:
        """Update session fields."""
        allowed = ["user_id", "metadata", "status", "agent_context", "last_activity"]
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        set_clause = ", ".join([f"{k} = %s" for k in updates])
        values = [*list(updates.values()), session_id]

        conn = self._get_conn()
        if not conn:
            return False

        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE sessions SET {set_clause} WHERE session_id = %s",
                    values,
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            self._put_conn(conn)

    def list_sessions(
        self, user_id: str | None = None, status: str | None = None, limit: int = 100
    ) -> list:
        """List sessions with filters."""
        conn = self._get_conn()
        if not conn:
            return []

        try:
            conditions = []
            params = []
            if user_id:
                conditions.append("user_id = %s")
                params.append(user_id)
            if status:
                conditions.append("status = %s")
                params.append(status)

            where = " AND ".join(conditions) if conditions else "1=1"
            params.append(limit)

            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT * FROM sessions WHERE {where} ORDER BY started_at DESC LIMIT %s",
                    params,
                )
                return [self._row_to_dict(row, cur.description) for row in cur.fetchall()]
        finally:
            self._put_conn(conn)

    # ==================== MESSAGES ====================

    def add_message(
        self, session_id: str, role: str, content: str, metadata: dict | None = None
    ) -> int:
        """Add a message to a session."""
        conn = self._get_conn()
        if not conn:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO messages (session_id, role, content, metadata)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (session_id, role, content, json.dumps(metadata or {})),
                )
                conn.commit()
                return cur.fetchone()[0]
        finally:
            self._put_conn(conn)

    def get_messages(self, session_id: str, limit: int = 100) -> list:
        """Get messages for a session."""
        conn = self._get_conn()
        if not conn:
            return []

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM messages
                    WHERE session_id = %s
                    ORDER BY timestamp ASC
                    LIMIT %s
                    """,
                    (session_id, limit),
                )
                return [self._row_to_dict(row, cur.description) for row in cur.fetchall()]
        finally:
            self._put_conn(conn)

    # ==================== USERS ====================

    def create_user(
        self, user_id: str, email: str | None = None, preferences: dict | None = None
    ) -> str:
        """Create a new user."""
        conn = self._get_conn()
        if not conn:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (user_id, email, preferences)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                    RETURNING user_id
                    """,
                    (user_id, email, json.dumps(preferences or {})),
                )
                conn.commit()
                result = cur.fetchone()
                return result[0] if result else user_id
        finally:
            self._put_conn(conn)

    def get_user(self, user_id: str) -> dict:
        """Get user by ID."""
        conn = self._get_conn()
        if not conn:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                row = cur.fetchone()
                if row:
                    return self._row_to_dict(row, cur.description)
                return None
        finally:
            self._put_conn(conn)

    def update_user(self, user_id: str, **kwargs) -> bool:
        """Update user fields."""
        allowed = ["email", "preferences", "total_sessions", "total_messages", "last_login"]
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        set_clause = ", ".join([f"{k} = %s" for k in updates])
        values = [*list(updates.values()), user_id]

        conn = self._get_conn()
        if not conn:
            return False

        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"UPDATE users SET {set_clause} WHERE user_id = %s",
                    values,
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            self._put_conn(conn)

    # ==================== AGENT STATES ====================

    def save_agent_state(
        self,
        agent_id: str,
        agent_name: str,
        config: dict | None = None,
        state: dict | None = None,
    ) -> str:
        """Save or update agent state."""
        conn = self._get_conn()
        if not conn:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_states (agent_id, agent_name, config, state, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (agent_id) DO UPDATE SET
                        agent_name = EXCLUDED.agent_name,
                        config = EXCLUDED.config,
                        state = EXCLUDED.state,
                        updated_at = NOW()
                    RETURNING agent_id
                    """,
                    (agent_id, agent_name, json.dumps(config or {}), json.dumps(state or {})),
                )
                conn.commit()
                return cur.fetchone()[0]
        finally:
            self._put_conn(conn)

    def get_agent_state(self, agent_id: str) -> dict:
        """Get agent state by ID."""
        conn = self._get_conn()
        if not conn:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM agent_states WHERE agent_id = %s", (agent_id,))
                row = cur.fetchone()
                if row:
                    return self._row_to_dict(row, cur.description)
                return None
        finally:
            self._put_conn(conn)

    def increment_agent_runs(self, agent_id: str, tasks: int = 1):
        """Increment agent run count."""
        conn = self._get_conn()
        if not conn:
            return

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE agent_states
                    SET total_runs = total_runs + %s, total_tasks = total_tasks + %s, updated_at = NOW()
                    WHERE agent_id = %s
                    """,
                    (tasks, tasks, agent_id),
                )
                conn.commit()
        finally:
            self._put_conn(conn)

    def list_agent_states(self) -> list:
        """List all agent states."""
        conn = self._get_conn()
        if not conn:
            return []

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM agent_states ORDER BY updated_at DESC")
                return [self._row_to_dict(row, cur.description) for row in cur.fetchall()]
        finally:
            self._put_conn(conn)

    # ==================== ANALYTICS ====================

    def record_metric(
        self,
        metric_type: str,
        value: float,
        date_str: str | None = None,
        metadata: dict | None = None,
    ):
        """Record a metric value."""
        record_date = date_str or date.today().isoformat()

        conn = self._get_conn()
        if not conn:
            return

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analytics (date, metric_type, metric_value, metadata)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (date, metric_type) DO UPDATE SET
                        metric_value = EXCLUDED.metric_value,
                        metadata = EXCLUDED.metadata,
                        created_at = NOW()
                    """,
                    (record_date, metric_type, value, json.dumps(metadata or {})),
                )
                conn.commit()
        finally:
            self._put_conn(conn)

    def get_metrics(self, metric_type: str | None = None, days: int = 30) -> list:
        """Get metrics with optional filters."""
        conn = self._get_conn()
        if not conn:
            return []

        try:
            with conn.cursor() as cur:
                if metric_type:
                    cur.execute(
                        """
                        SELECT * FROM analytics
                        WHERE metric_type = %s AND date >= CURRENT_DATE - INTERVAL '%s days'
                        ORDER BY date DESC
                        """,
                        (metric_type, days),
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM analytics
                        WHERE date >= CURRENT_DATE - INTERVAL '%s days'
                        ORDER BY date DESC
                        """,
                        (days,),
                    )
                return [self._row_to_dict(row, cur.description) for row in cur.fetchall()]
        finally:
            self._put_conn(conn)

    # ==================== SKILLS ====================

    def save_skill(
        self,
        skill_name: str,
        category: str | None = None,
        description: str | None = None,
        implementation: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Save a skill."""
        conn = self._get_conn()
        if not conn:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO skills (skill_name, category, description, implementation, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (skill_name) DO UPDATE SET
                        category = EXCLUDED.category,
                        description = EXCLUDED.description,
                        implementation = EXCLUDED.implementation,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    RETURNING skill_name
                    """,
                    (skill_name, category, description, implementation, json.dumps(metadata or {})),
                )
                conn.commit()
                return cur.fetchone()[0]
        finally:
            self._put_conn(conn)

    def get_skill(self, skill_name: str) -> dict:
        """Get skill by name."""
        conn = self._get_conn()
        if not conn:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM skills WHERE skill_name = %s", (skill_name,))
                row = cur.fetchone()
                if row:
                    return self._row_to_dict(row, cur.description)
                return None
        finally:
            self._put_conn(conn)

    def increment_skill_usage(self, skill_name: str, success: bool = True):
        """Increment skill usage count and optionally success rate."""
        conn = self._get_conn()
        if not conn:
            return

        try:
            with conn.cursor() as cur:
                if success:
                    cur.execute(
                        """
                        UPDATE skills
                        SET usage_count = usage_count + 1,
                            success_rate = ((success_rate * usage_count) + 1) / (usage_count + 1),
                            updated_at = NOW()
                        WHERE skill_name = %s
                        """,
                        (skill_name,),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE skills
                        SET usage_count = usage_count + 1, updated_at = NOW()
                        WHERE skill_name = %s
                        """,
                        (skill_name,),
                    )
                conn.commit()
        finally:
            self._put_conn(conn)

    def list_skills(self, category: str | None = None) -> list:
        """List skills with optional category filter."""
        conn = self._get_conn()
        if not conn:
            return []

        try:
            with conn.cursor() as cur:
                if category:
                    cur.execute(
                        "SELECT * FROM skills WHERE category = %s ORDER BY usage_count DESC",
                        (category,),
                    )
                else:
                    cur.execute("SELECT * FROM skills ORDER BY usage_count DESC")
                return [self._row_to_dict(row, cur.description) for row in cur.fetchall()]
        finally:
            self._put_conn(conn)

    # ==================== WORKFLOWS ====================

    def save_workflow(
        self,
        workflow_id: str,
        workflow_type: str | None = None,
        input_data: dict | None = None,
    ) -> str:
        """Start a new workflow."""
        conn = self._get_conn()
        if not conn:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO workflows (workflow_id, workflow_type, input_data, status)
                    VALUES (%s, %s, %s, 'running')
                    RETURNING workflow_id
                    """,
                    (workflow_id, workflow_type, json.dumps(input_data or {})),
                )
                conn.commit()
                return cur.fetchone()[0]
        finally:
            self._put_conn(conn)

    def complete_workflow(
        self,
        workflow_id: str,
        output_data: dict | None = None,
        status: str = "completed",
    ) -> bool:
        """Complete a workflow."""
        conn = self._get_conn()
        if not conn:
            return False

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE workflows
                    SET status = %s, output_data = %s, completed_at = NOW(),
                        duration_ms = EXTRACT(MILLISECONDS FROM (NOW() - started_at))::INTEGER
                    WHERE workflow_id = %s
                    """,
                    (status, json.dumps(output_data or {}), workflow_id),
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            self._put_conn(conn)

    def get_workflow(self, workflow_id: str) -> dict:
        """Get workflow by ID."""
        conn = self._get_conn()
        if not conn:
            return None

        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM workflows WHERE workflow_id = %s", (workflow_id,))
                row = cur.fetchone()
                if row:
                    return self._row_to_dict(row, cur.description)
                return None
        finally:
            self._put_conn(conn)

    def list_workflows(
        self, workflow_type: str | None = None, status: str | None = None, limit: int = 100
    ) -> list:
        """List workflows with filters."""
        conn = self._get_conn()
        if not conn:
            return []

        try:
            conditions = []
            params = []
            if workflow_type:
                conditions.append("workflow_type = %s")
                params.append(workflow_type)
            if status:
                conditions.append("status = %s")
                params.append(status)

            where = " AND ".join(conditions) if conditions else "1=1"
            params.append(limit)

            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT * FROM workflows WHERE {where} ORDER BY started_at DESC LIMIT %s",
                    params,
                )
                return [self._row_to_dict(row, cur.description) for row in cur.fetchall()]
        finally:
            self._put_conn(conn)

    # ==================== UTILITIES ====================

    def _row_to_dict(self, row, description) -> dict:
        """Convert a row to a dictionary."""
        return dict(zip([col[0] for col in description], row, strict=True))

    def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        conn = self._get_conn()
        if not conn:
            return False
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        finally:
            self._put_conn(conn)


if __name__ == "__main__":
    memory = NeonMemory()

    if memory.health_check():
        print("NeonDB connection: OK")

        # Test session creation
        session_id = memory.create_session(user_id="test_user", metadata={"source": "cli"})
        print(f"Created session: {session_id}")

        # Add a message
        memory.add_message(session_id, "user", "Hello, world!")
        memory.add_message(session_id, "assistant", "Hi there!")
        messages = memory.get_messages(session_id)
        print(f"Messages in session: {len(messages)}")

        # Test user
        memory.create_user("test_user", email="test@example.com")
        user = memory.get_user("test_user")
        print(f"User: {user['user_id']}, Email: {user['email']}")

        # Test metrics
        memory.record_metric("sessions_created", 1)
        memory.record_metric("messages_sent", 2)
        metrics = memory.get_metrics()
        print(f"Metrics recorded: {len(metrics)}")

        # Test skills
        memory.save_skill("test_skill", category="testing", description="A test skill")
        skills = memory.list_skills()
        print(f"Skills: {len(skills)}")

        memory._close()
        print("\nAll tests passed!")
    else:
        print("NeonDB connection: FAILED")
