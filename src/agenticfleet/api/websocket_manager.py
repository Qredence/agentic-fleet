"""WebSocket connection manager for streaming workflow events."""

import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time workflow streaming."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, execution_id: str) -> None:
        """Accept and register a WebSocket connection.

        Args:
            websocket: WebSocket connection to register
            execution_id: Execution ID for this connection
        """
        await websocket.accept()

        if execution_id not in self.active_connections:
            self.active_connections[execution_id] = []

        self.active_connections[execution_id].append(websocket)
        logger.info(f"WebSocket connected for execution {execution_id}")

    def disconnect(self, websocket: WebSocket, execution_id: str) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
            execution_id: Execution ID for this connection
        """
        if execution_id in self.active_connections:
            if websocket in self.active_connections[execution_id]:
                self.active_connections[execution_id].remove(websocket)

            if not self.active_connections[execution_id]:
                del self.active_connections[execution_id]

        logger.info(f"WebSocket disconnected for execution {execution_id}")

    async def send_json(self, data: dict[str, Any], execution_id: str) -> None:
        """Send JSON data to all connections for an execution.

        Args:
            data: Data to send as JSON
            execution_id: Execution ID to send to
        """
        if execution_id not in self.active_connections:
            return

        # Send to all connections, removing any that fail
        disconnected: list[WebSocket] = []

        for connection in self.active_connections[execution_id]:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws, execution_id)

    async def send_text(self, message: str, execution_id: str) -> None:
        """Send text message to all connections for an execution.

        Args:
            message: Text message to send
            execution_id: Execution ID to send to
        """
        if execution_id not in self.active_connections:
            return

        # Send to all connections, removing any that fail
        disconnected: list[WebSocket] = []

        for connection in self.active_connections[execution_id]:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws, execution_id)

    def has_connections(self, execution_id: str) -> bool:
        """Check if there are active connections for an execution.

        Args:
            execution_id: Execution ID to check

        Returns:
            True if there are active connections
        """
        return execution_id in self.active_connections and bool(
            self.active_connections[execution_id]
        )

    def get_connection_count(self, execution_id: str) -> int:
        """Get number of active connections for an execution.

        Args:
            execution_id: Execution ID to check

        Returns:
            Number of active connections
        """
        if execution_id not in self.active_connections:
            return 0
        return len(self.active_connections[execution_id])
