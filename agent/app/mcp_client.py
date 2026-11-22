from __future__ import annotations

import os

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


def mcp_url() -> str:
    return os.getenv("MCP_URL", "http://localhost:8002/mcp")


async def search_billing_documentation(query: str) -> str:
    async with streamable_http_client(mcp_url()) as streams:
        read_stream, write_stream = streams[0], streams[1]
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "search_billing_documentation",
                {"query": query},
            )
    parts: list[str] = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    body = "\n".join(parts).strip()
    if getattr(result, "isError", False):
        return f"Error: {body or 'MCP tool failed'}"
    return body or "No matching billing policy section was found."
