#!/usr/bin/env python3
"""fleet-agent - Context-aware development assistant with dual memory (NeonDB + ChromaDB)."""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
import yaml
from psycopg2 import pool

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
os.chdir(Path(__file__).resolve().parent.parent.parent.parent)


def get_neon_pool():
    """Get NeonDB connection pool."""
    config_path = ".fleet/context/.neon/config.yaml"
    if not Path(config_path).exists():
        return None

    with open(config_path) as f:
        config = yaml.safe_load(f)

    cloud = config.get("cloud", {})
    pooling = config.get("pooling", {})

    try:
        return pool.ThreadedConnectionPool(
            minconn=pooling.get("min_size", 2),
            maxconn=pooling.get("max_size", 10),
            host=cloud.get("host"),
            database=cloud.get("database"),
            user=cloud.get("user"),
            password=cloud.get("password"),
            sslmode="require",
        )
    except Exception:
        return None


def get_chroma_client():
    """Get ChromaDB client."""
    config_path = ".fleet/context/.chroma/config.yaml"
    if not Path(config_path).exists():
        return None

    with open(config_path) as f:
        config = yaml.safe_load(f)

    cloud = config.get("cloud", {})

    try:
        return chromadb.CloudClient(
            tenant=cloud.get("tenant"),
            database=cloud.get("database"),
            api_key=cloud.get("api_key"),
        )
    except Exception:
        return None


class FleetAgent:
    """Context-aware development assistant with dual memory."""

    def __init__(self):
        self.session_id = None

    def _get_or_create_session(self) -> str:
        """Get existing session or create new one."""
        conn_pool = get_neon_pool()
        if not conn_pool:
            return "no-session"

        try:
            conn = conn_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT session_id FROM sessions WHERE status = 'active' ORDER BY last_activity DESC LIMIT 1"
                    )
                    row = cur.fetchone()
                    if row:
                        session_id = row[0]
                        print(f"Resumed session: {session_id}")
                        return session_id

                    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    cur.execute(
                        "INSERT INTO sessions (session_id, status) VALUES (%s, 'active')",
                        (session_id,),
                    )
                    conn.commit()
                    print(f"Created session: {session_id}")
                    return session_id
            finally:
                conn_pool.putconn(conn)
        finally:
            conn_pool.closeall()

    def learn_pattern(self, name: str, category: str, content: str):
        """Save pattern to both NeonDB and ChromaDB."""
        if not self.session_id:
            self.session_id = self._get_or_create_session()

        # 1. Save to NeonDB
        conn_pool = get_neon_pool()
        if conn_pool:
            conn = conn_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO skills (skill_name, category, implementation, metadata)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (skill_name) DO UPDATE SET
                            category = EXCLUDED.category,
                            implementation = EXCLUDED.implementation,
                            metadata = EXCLUDED.metadata,
                            updated_at = NOW()
                        RETURNING skill_name
                        """,
                        (name, category, content, f'{{"session_id": "{self.session_id}"}}'),
                    )
                    conn.commit()
                    print(f"  Saved to NeonDB: {name}")
            finally:
                conn_pool.putconn(conn)
                conn_pool.closeall()

        # 2. Index to ChromaDB
        client = get_chroma_client()
        if client:
            try:
                config_path = ".fleet/context/.chroma/config.yaml"
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                coll_name = config.get("collections", {}).get(
                    "procedural", "agentic-fleet-procedural"
                )

                try:
                    collection = client.get_collection(name=coll_name)
                except Exception:
                    collection = client.create_collection(name=coll_name)

                doc_id = f"pattern_{name.replace(' ', '_').lower()}"
                collection.upsert(
                    documents=[content],
                    ids=[doc_id],
                    metadatas=[
                        {
                            "name": name,
                            "type": "pattern",
                            "category": category,
                            "session_id": self.session_id,
                            "created_at": datetime.now().isoformat(),
                        }
                    ],
                )
                print(f"  Indexed to ChromaDB: {doc_id}")
            except Exception as e:
                print(f"  ChromaDB warning: {e}")

        print(f"  Learned pattern: {name} ({category})")

    def recall(self, query: str, n_results: int = 5) -> dict:
        """Search both NeonDB and ChromaDB."""
        results: dict[str, Any] = {"neon": [], "chroma": {}}

        # 1. Search NeonDB
        conn_pool = get_neon_pool()
        if conn_pool:
            conn = conn_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT skill_name, category, description, implementation, usage_count, success_rate
                        FROM skills
                        WHERE skill_name ILIKE %s OR category ILIKE %s
                        ORDER BY usage_count DESC
                        LIMIT %s
                        """,
                        (f"%{query}%", f"%{query}%", n_results),
                    )
                    for row in cur.fetchall():
                        results["neon"].append(
                            {
                                "name": row[0],
                                "category": row[1],
                                "description": row[2],
                                "implementation": row[3],
                                "usage_count": row[4],
                                "success_rate": row[5],
                            }
                        )
            finally:
                conn_pool.putconn(conn)
                conn_pool.closeall()

        # 2. Search ChromaDB
        client = get_chroma_client()
        if client:
            try:
                config_path = ".fleet/context/.chroma/config.yaml"
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                collections = config.get("collections", {})

                for coll_key in ["procedural", "semantic"]:
                    coll_name = collections.get(coll_key)
                    if not coll_name:
                        continue

                    try:
                        collection = client.get_collection(name=coll_name)
                        search_results = collection.query(query_texts=[query], n_results=n_results)
                        if search_results["documents"]:
                            results["chroma"][coll_key] = search_results
                    except Exception:
                        pass
            except Exception:
                pass

        return results

    def get_context(self, task: str) -> dict:
        """Load relevant context blocks based on task keywords."""
        if not self.session_id:
            self.session_id = self._get_or_create_session()

        blocks = []
        task_lower = task.lower()

        keyword_map = {
            "agent": "core/project.md",
            "add agent": "core/project.md",
            "create agent": "core/project.md",
            "workflow": "workflows/supervisor.py",
            "create workflow": "workflows/supervisor.py",
            "dspy": "dspy_modules/reasoner.py",
            "signature": "dspy_modules/signatures.py",
            "typed": "dspy_modules/typed_models.py",
            "test": "core/commands.md",
            "make test": "core/commands.md",
            "lint": "blocks/project/gotchas.md",
            "check": "blocks/project/gotchas.md",
            "git": "blocks/workflows/git.md",
            "commit": "blocks/workflows/git.md",
            "pr": "blocks/workflows/review.md",
            "review": "blocks/workflows/review.md",
            "memory": ".fleet/context/MEMORY.md",
            "neon": ".fleet/context/.neon/config.yaml",
            "chroma": ".fleet/context/.chroma/config.yaml",
        }

        for keyword, block_path in keyword_map.items():
            if keyword in task_lower:
                full_path = (
                    f".fleet/context/{block_path}" if not block_path.startswith(".") else block_path
                )
                try:
                    content = Path(full_path).read_text()
                    blocks.append(
                        {
                            "source": block_path,
                            "content": content[:5000],
                            "matched_keyword": keyword,
                        }
                    )
                except Exception:
                    pass

        return {
            "session_id": self.session_id,
            "blocks_loaded": len(blocks),
            "blocks": blocks,
        }

    def analyze_code(self, file_path: str) -> dict[str, Any]:
        """Analyze code file for patterns."""
        if not Path(file_path).exists():
            return {"error": f"File not found: {file_path}"}

        content = Path(file_path).read_text()
        analysis: dict[str, list[dict[str, Any]] | str] = {
            "file_path": file_path,
            "dspy_signatures": [],
            "agents": [],
            "workflows": [],
        }

        for i, line in enumerate(content.split("\n")):
            if "class " in line and "dspy.Signature" in line:
                sig_name = line.split("class ")[1].split("(")[0].strip()
                analysis["dspy_signatures"].append({"name": sig_name, "line": i + 1})

            if "def create_agent" in line or "AgentFactory" in line:
                analysis["agents"].append({"name": line.strip()[:100], "line": i + 1})

            if "class " in line and "Executor" in line:
                exec_name = line.split("class ")[1].split("(")[0].strip()
                analysis["workflows"].append({"name": exec_name, "line": i + 1})

        return analysis

    def session_start(self) -> str:
        """Start a new session."""
        self.session_id = self._get_or_create_session()
        return self.session_id

    def session_status(self) -> dict:
        """Get current session status."""
        if not self.session_id:
            self.session_id = self._get_or_create_session()

        conn_pool = get_neon_pool()
        if not conn_pool:
            return {"session_id": self.session_id}

        conn = conn_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status, started_at FROM sessions WHERE session_id = %s",
                    (self.session_id,),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "session_id": self.session_id,
                        "status": row[0],
                        "started_at": str(row[1]),
                    }
        finally:
            conn_pool.putconn(conn)
            conn_pool.closeall()

        return {"session_id": self.session_id}

    def session_summary(self, summary: str):
        """Save session summary."""
        if not self.session_id:
            self.session_id = self._get_or_create_session()

        conn_pool = get_neon_pool()
        if conn_pool:
            conn = conn_pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE sessions SET metadata = %s, status = 'completed' WHERE session_id = %s",
                        (f'{{"summary": "{summary}"}}', self.session_id),
                    )
                    conn.commit()
                    print("  Saved session summary")
            finally:
                conn_pool.putconn(conn)
                conn_pool.closeall()

    def stats(self) -> dict:
        """Show development statistics."""
        conn_pool = get_neon_pool()
        if not conn_pool:
            return {"error": "No database connection"}

        stats = {}
        conn = conn_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM skills")
                stats["total_skills"] = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM sessions")
                stats["total_sessions"] = cur.fetchone()[0]

                cur.execute(
                    "SELECT COUNT(*) FROM sessions WHERE started_at > NOW() - INTERVAL '7 days'"
                )
                stats["sessions_this_week"] = cur.fetchone()[0]

                cur.execute(
                    "SELECT skill_name, category, usage_count FROM skills ORDER BY usage_count DESC LIMIT 5"
                )
                stats["top_skills"] = [
                    {"name": r[0], "category": r[1], "usage": r[2]} for r in cur.fetchall()
                ]
        finally:
            conn_pool.putconn(conn)
            conn_pool.closeall()

        return stats


def main():
    """Run fleet-agent CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fleet Agent - Context-aware development assistant"
    )
    subparsers = parser.add_subparsers(dest="command")

    learn_p = subparsers.add_parser("learn", help="Learn a pattern")
    learn_p.add_argument("--name", required=True)
    learn_p.add_argument("--category", required=True)
    learn_p.add_argument("--content", required=True)

    recall_p = subparsers.add_parser("recall", help="Search memory")
    recall_p.add_argument("query")
    recall_p.add_argument("--n", type=int, default=5)

    context_p = subparsers.add_parser("context", help="Get context for task")
    context_p.add_argument("task")

    analyze_p = subparsers.add_parser("analyze", help="Analyze code file")
    analyze_p.add_argument("file")

    session_p = subparsers.add_parser("session", help="Session management")
    session_sub = session_p.add_subparsers(dest="session_command")
    session_sub.add_parser("start")
    session_sub.add_parser("status")
    session_sub.add_parser("summary")
    session_sub.add_parser("list")

    subparsers.add_parser("stats", help="Show statistics")

    args = parser.parse_args()
    agent = FleetAgent()

    if args.command == "learn":
        agent.learn_pattern(args.name, args.category, args.content)

    elif args.command == "recall":
        results = agent.recall(args.query, args.n)
        print("\n=== NEONDB ===")
        for skill in results["neon"]:
            print(f"  - {skill['name']} ({skill['category']})")
        print("\n=== CHROMADB ===")
        for coll_key, coll_results in results.get("chroma", {}).items():
            print(f"\n  {coll_key.upper()}:")
            for i, (_, meta) in enumerate(
                zip(coll_results["documents"][0], coll_results["metadatas"][0], strict=True)
            ):
                print(f"    [{i + 1}] {meta.get('name', 'Unknown')}")

    elif args.command == "context":
        ctx = agent.get_context(args.task)
        print(f"\nSession: {ctx['session_id']}")
        print(f"Blocks: {ctx['blocks_loaded']}")
        for block in ctx.get("blocks", []):
            print(f"  - {block['source']} ({block['matched_keyword']})")

    elif args.command == "analyze":
        analysis = agent.analyze_code(args.file)
        if "error" in analysis:
            print(f"Error: {analysis['error']}")
        else:
            print(f"\n{analysis['file_path']}")
            print(f"  DSPy signatures: {len(analysis['dspy_signatures'])}")
            print(f"  Agents: {len(analysis['agents'])}")
            print(f"  Workflows: {len(analysis['workflows'])}")

    elif args.command == "session":
        if args.session_command == "start":
            agent.session_start()
        elif args.session_command == "status":
            status = agent.session_status()
            print(f"\nSession: {status.get('session_id', 'N/A')}")
            print(f"  Status: {status.get('status', 'N/A')}")
        elif args.session_command == "summary":
            agent.session_summary("Manual summary")

    elif args.command == "stats":
        stats = agent.stats()
        if "error" in stats:
            print(f"Error: {stats['error']}")
        else:
            print("\n=== Statistics ===")
            print(f"  Skills: {stats.get('total_skills', 0)}")
            print(f"  Sessions: {stats.get('total_sessions', 0)}")
            print(f"  This week: {stats.get('sessions_this_week', 0)}")


if __name__ == "__main__":
    main()
