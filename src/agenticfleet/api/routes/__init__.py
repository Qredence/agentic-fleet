from __future__ import annotations

from fastapi import FastAPI

from agenticfleet.api.routes import approvals, chat, conversations, legacy, placeholders, system, workflows

ROUTERS = (
    system.router,
    placeholders.router,
    conversations.router,
    chat.router,
    legacy.router,
    approvals.router,
    workflows.router,
)


def register_routes(app: FastAPI) -> None:
    for router in ROUTERS:
        app.include_router(router)
