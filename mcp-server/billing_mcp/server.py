from __future__ import annotations

import os
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from billing_mcp.indexer import BillingIndex

GUIDE_PATH = Path(
    os.getenv(
        "BILLING_GUIDE_PATH",
        Path(__file__).resolve().parent.parent / "docs" / "Mobile_Provider_Billing_Guide.md",
    )
)

INDEX = BillingIndex.from_file(GUIDE_PATH)
print(f"Indexed {INDEX.chunk_count} billing guide sections from {GUIDE_PATH}", flush=True)

mcp = MCPServer(
    name="billing-documentation",
    instructions=(
        "Search the indexed mobile provider billing guide. "
        "The guide explains allowances, pricing, cycles, partial payments, disputes, and late payments. "
        "It is not the live billing database."
    ),
)


@mcp.tool(
    name="search_billing_documentation",
    description=(
        "Search the indexed mobile provider billing guide. "
        "Use this for allowances, phone pricing, extra data charges, billing cycles, "
        "partial payments, disputes, late payments, and payment confirmation rules. "
        "Returns relevant excerpts and section references. This does not return a live bill."
    ),
)
def search_billing_documentation(query: str) -> str:
    return INDEX.search_text(query)


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "mcp-server", "chunks": INDEX.chunk_count})


def main() -> None:
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )


if __name__ == "__main__":
    main()
