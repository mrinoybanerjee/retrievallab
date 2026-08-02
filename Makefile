.PHONY: setup dev test lint build demo-pdf benchmark phase0-fixture phase0 verify-research multiconir

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

phase0-fixture:
	uv run python scripts/build_phase0_fixture.py

phase0: phase0-fixture
	uv run python scripts/run_phase0.py

verify-research:
	uv run python scripts/verify_phase0_artifacts.py

multiconir:
	@test -n "$(MULTICONIR_SOURCE)" || (echo "Set MULTICONIR_SOURCE to a pinned EIT-NLP/MultiConIR checkout." && exit 2)
	uv run python scripts/prepare_multiconir.py --source "$(MULTICONIR_SOURCE)" --output data/external/multiconir-task2-probe.json --query-format structured --seed 1729
	uv run python scripts/run_phase0.py --suite data/external/multiconir-task2-probe.json --output data/benchmarks/multiconir-task2-structured-9884fb3e.json --web-output apps/web/public/benchmarks/multiconir-task2-structured-9884fb3e.json --repeats 1 --bootstrap-samples 5000 --case-payload-limit 10
