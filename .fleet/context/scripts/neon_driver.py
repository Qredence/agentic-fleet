"""NeonDB driver for structured memory storage."""

import logging
import os

import yaml
from psycopg2 import pool

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class NeonDriver:
    """Driver for managing NeonDB structured memory storage."""

    def __init__(self, config_path=".fleet/context/.neon/config.yaml"):
        self.config = self._load_config(config_path)
        self.pool = self._create_pool()
        self.initialized = False

    def _load_config(self, path):
        """Load configuration from YAML file."""
        if not os.path.exists(path):
            logger.warning(f"Config file not found at {path}. Operating in offline mode.")
            return {}

        with open(path) as f:
            return yaml.safe_load(f)

    def _create_pool(self):
        """Create connection pool from config."""
        cloud_config = self.config.get("cloud", {})

        host = cloud_config.get("host")
        database = cloud_config.get("database")
        user = cloud_config.get("user")
        password = cloud_config.get("password")

        if not all([host, database, user, password]):
            logger.warning("NeonDB credentials incomplete. Operating in offline mode.")
            return None

        pooling_config = self.config.get("pooling", {})
        ssl_config = self.config.get("ssl", {})

        try:
            conn_pool = pool.ThreadedConnectionPool(
                minconn=pooling_config.get("min_size", 2),
                maxconn=pooling_config.get("max_size", 10),
                host=host,
                database=database,
                user=user,
                password=password,
                sslmode="require" if ssl_config.get("enabled", True) else "disable",
            )
            logger.info(f"Connected to NeonDB (Host: {host}, DB: {database})")
            return conn_pool
        except Exception as e:
            logger.error(f"Failed to connect to NeonDB: {e}")
            return None

    def execute_query(self, query, params=None, fetch=False):
        """Execute a query with optional fetch."""
        if not self.pool:
            logger.warning("NeonDB pool not initialized. Skipping query.")
            return None

        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if fetch:
                    return cur.fetchall()
                conn.commit()
                return cur.rowcount
        finally:
            self.pool.putconn(conn)

    def execute_many(self, query, params_list):
        """Execute a query with multiple parameter sets."""
        if not self.pool:
            logger.warning("NeonDB pool not initialized. Skipping query.")
            return None

        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.executemany(query, params_list)
                conn.commit()
                return cur.rowcount
        finally:
            self.pool.putconn(conn)

    def fetch_one(self, query, params=None):
        """Fetch a single row."""
        if not self.pool:
            logger.warning("NeonDB pool not initialized. Skipping query.")
            return None

        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()
        finally:
            self.pool.putconn(conn)

    def fetch_all(self, query, params=None):
        """Fetch all rows."""
        if not self.pool:
            logger.warning("NeonDB pool not initialized. Skipping query.")
            return []

        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()
        finally:
            self.pool.putconn(conn)

    def close(self):
        """Close all connections in the pool."""
        if self.pool:
            self.pool.closeall()
            logger.info("NeonDB connection pool closed")


if __name__ == "__main__":
    driver = NeonDriver()
    if driver.pool:
        result = driver.execute_query("SELECT 1", fetch=True)
        print(f"Test query result: {result}")
        driver.close()
