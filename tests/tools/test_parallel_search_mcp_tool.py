"""Exercise the real factory, MCP transport, registry and agent tool dispatch."""

import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest
import yaml
from agent_framework import ChatAgent, ChatMessage, ChatResponse, FunctionCallContent
from agent_framework._clients import BaseChatClient
from agent_framework._tools import use_function_invocation
from agent_framework.exceptions import ToolExecutionException
from mcp.client.streamable_http import streamablehttp_client

from agentic_fleet.agents.coordinator import AgentFactory
from agentic_fleet.tools import ParallelSearchMCPTool

URL = "https://search.parallel.ai/mcp"
USER_AGENT = "agentic-fleet (https://github.com/Qredence/agentic-fleet)"
SOURCE = "https://docs.python.org/3/library/asyncio.html"


@pytest.fixture
def mcp_requests(monkeypatch):
    requests = []
    schemas = [
        {
            "name": "web_search",
            "description": "Search the web",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "objective": {"type": "string"},
                    "search_queries": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["objective", "search_queries"],
            },
        },
        {
            "name": "web_fetch",
            "description": "Fetch web pages",
            "inputSchema": {
                "type": "object",
                "properties": {"urls": {"type": "array", "items": {"type": "string"}}},
                "required": ["urls"],
            },
        },
    ]

    def handler(request):
        assert str(request.url) == URL
        assert request.headers["user-agent"] == USER_AGENT
        assert "authorization" not in request.headers
        if request.method != "POST":
            return httpx.Response(405)
        body = json.loads(request.content)
        requests.append(body)
        method = body["method"]
        if "id" not in body:
            return httpx.Response(202)
        if method == "initialize":
            result = {
                "protocolVersion": body["params"]["protocolVersion"],
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "parallel-fixture", "version": "1"},
            }
        elif method == "tools/list":
            result = {"tools": schemas}
        elif method == "tools/call":
            result = {
                "content": [{"type": "text", "text": f"{SOURCE}\nAsyncio supports async/await."}],
                "isError": False,
            }
        else:
            raise AssertionError(f"Unexpected MCP method: {method}")
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result})

    def client_factory(headers=None, timeout=None, auth=None):
        return httpx.AsyncClient(
            headers=headers, timeout=timeout, auth=auth, transport=httpx.MockTransport(handler)
        )

    def transport(**kwargs):
        return streamablehttp_client(**kwargs, httpx_client_factory=client_factory)

    monkeypatch.setattr("agent_framework._mcp.streamablehttp_client", transport)
    # Deliberately present keys: this adapter must still connect anonymously.
    monkeypatch.setenv("PARALLEL_API_KEY", "must-not-be-used")
    monkeypatch.setenv("TAVILY_API_KEY", "must-not-be-used")
    return requests


async def test_factory_registry_search(mcp_requests):
    factory = AgentFactory()
    tools = factory._resolve_tools(["ParallelSearchMCPTool"])
    assert len(tools) == 1
    tool = tools[0]
    assert isinstance(tool, ParallelSearchMCPTool)
    factory.tool_registry.register_tool_by_agent("researcher", tool)
    result = await factory.tool_registry.execute_tool(
        "parallel_search",
        query="Find asyncio documentation",
        search_queries=["Python asyncio docs"],
    )
    assert SOURCE in result
    assert "async/await" in result
    call = next(r for r in mcp_requests if r["method"] == "tools/call")
    assert call["params"] == {
        "name": "web_search",
        "arguments": {
            "objective": "Find asyncio documentation",
            "search_queries": ["Python asyncio docs"],
        },
    }
    assert not tool.is_connected
    assert factory._resolve_tools(["ParallelSearchMCPTool"])[0] is tool


@use_function_invocation
class SearchThenFetchClient(BaseChatClient):
    """Deterministic model fixture requesting both discovered MCP functions."""

    def __init__(self):
        super().__init__()
        self.calls = 0

    async def _inner_get_response(self, *, messages, chat_options, **kwargs):
        self.calls += 1
        names = {t.name for t in chat_options.tools}
        assert {"web_search", "web_fetch"} <= names
        if self.calls == 1:
            call = FunctionCallContent(
                call_id="search",
                name="web_search",
                arguments={"objective": "Find asyncio docs", "search_queries": ["Python asyncio"]},
            )
        elif self.calls == 2:
            assert SOURCE in json.dumps(messages[-1].to_dict())
            call = FunctionCallContent(
                call_id="fetch", name="web_fetch", arguments={"urls": [SOURCE]}
            )
        else:
            assert SOURCE in json.dumps(messages[-1].to_dict())
            return ChatResponse(
                messages=[ChatMessage(role="assistant", text=f"Asyncio docs: {SOURCE}")]
            )
        return ChatResponse(messages=[ChatMessage(role="assistant", contents=[call])])

    async def _inner_get_streaming_response(self, **kwargs):
        raise NotImplementedError
        yield  # pragma: no cover


async def test_agent_loop_search_and_fetch(mcp_requests):
    tool = AgentFactory()._resolve_tools(["ParallelSearchMCPTool"])[0]
    client = SearchThenFetchClient()
    async with tool:
        agent = ChatAgent(name="researcher", chat_client=client, tools=[tool])
        result = await agent.run("Find and read the asyncio docs")
    assert SOURCE in result.text
    assert client.calls == 3
    calls = [r["params"] for r in mcp_requests if r["method"] == "tools/call"]
    assert [c["name"] for c in calls] == ["web_search", "web_fetch"]
    assert calls[1]["arguments"] == {"urls": [SOURCE]}
    assert not tool.is_connected


@pytest.mark.parametrize("error", [ToolExecutionException("offline"), asyncio.CancelledError()])
async def test_failure_and_cancellation_disconnect(monkeypatch, error):
    tool = ParallelSearchMCPTool()
    monkeypatch.setattr(tool, "_ensure_connection", AsyncMock())
    monkeypatch.setattr(tool, "call_tool", AsyncMock(side_effect=error))
    disconnect = AsyncMock()
    monkeypatch.setattr(tool, "close", disconnect)
    with pytest.raises(type(error)):
        await tool.run("Python asyncio")
    disconnect.assert_awaited_once()


async def test_default_query_and_empty_response(monkeypatch):
    tool = ParallelSearchMCPTool()
    monkeypatch.setattr(tool, "_ensure_connection", AsyncMock())
    call = AsyncMock(return_value=[])
    monkeypatch.setattr(tool, "call_tool", call)
    monkeypatch.setattr(tool, "close", AsyncMock())
    assert await tool.run("Python asyncio") == "Parallel returned an empty response."
    call.assert_awaited_once_with(
        "web_search", objective="Python asyncio", search_queries=["Python asyncio"]
    )


def test_shipped_selection_is_unchanged():
    from agentic_fleet.agents.coordinator import _resolve_workflow_config_path

    config = yaml.safe_load(_resolve_workflow_config_path().read_text())
    assert "TavilySearchTool" in config["agents"]["researcher"]["tools"]
    assert "ParallelSearchMCPTool" not in config["agents"]["researcher"]["tools"]


async def test_concurrent_registry_runs_reconnect(mcp_requests):
    tool = ParallelSearchMCPTool()
    results = await asyncio.gather(tool.run("Python asyncio"), tool.run("Python coroutines"))
    assert all(SOURCE in result for result in results)
    assert sum(r["method"] == "initialize" for r in mcp_requests) == 2
    assert not tool.is_connected
