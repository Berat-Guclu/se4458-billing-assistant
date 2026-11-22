.PHONY: test up

test:
	cd billing-api && ../.venv/bin/pytest
	cd mcp-server && ../.venv/bin/pytest
	cd agent && ../.venv/bin/pytest

up:
	docker compose up --build
