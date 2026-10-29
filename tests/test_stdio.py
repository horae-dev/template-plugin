# SPDX-License-Identifier: Apache-2.0
"""The plugin runs as an MCP server over stdio, as the core's plugin host starts it."""

import sys

import anyio
from horae_sdk.testing import read_result
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters


async def serve_and_call() -> tuple[set[str], object, list[object]]:
    server = StdioServerParameters(command=sys.executable, args=["-m", "example_plugin"])
    async with Client(server, read_timeout_seconds=30) as client:
        tools = {tool.name for tool in (await client.list_tools()).tools}
        replayed = read_result(await client.call_tool("example.inbox", {"folder": "news"}))
    return tools, replayed.data, replayed.intents


def test_serves_over_stdio() -> None:
    tools, data, intents = anyio.run(serve_and_call)
    assert "example.inbox" in tools
    assert data == {"folder": "news", "messages": [{"id": "welcome", "subject": "Welcome to news"}]}
    assert intents == [
        {
            "type": "task.create",
            "title": "Reply to Welcome to news",
            "fingerprint": "example:reply:welcome",
        }
    ]
