.PHONY: setup dev test lint build demo-pdf benchmark

setup:
	uv sync --extra dev
	cd apps/web && pnpm install --ignore-scripts
	uv run python scripts/build_demo_pdf.py

dev:
	@echo "Run the API and web commands in separate terminals; see README.md."

test:
	uv run pytest

lint:
	uv run ruff check .
	cd apps/web && pnpm lint

build:
	cd apps/web && pnpm build

demo-pdf:
	uv run python scripts/build_demo_pdf.py

benchmark:
	uv run python scripts/run_benchmark.py
