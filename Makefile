.PHONY: bootstrap check test compose-up compose-down

bootstrap:
	uv sync --all-groups
	cd apps/web && pnpm install

check:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy apps packages
	uv run pytest
	cd apps/web && pnpm lint && pnpm typecheck && pnpm test && pnpm build

test:
	uv run pytest
	cd apps/web && pnpm test

compose-up:
	docker compose up --build

compose-down:
	docker compose down

