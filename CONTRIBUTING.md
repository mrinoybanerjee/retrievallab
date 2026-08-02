# Contributing

Thank you for improving RetrievalLab.

1. Open an issue for behavior changes or new retrieval strategies.
2. Create a focused branch and keep unrelated formatting out of the diff.
3. Run `uv run pytest`, `uv run ruff check .`, and `pnpm --dir apps/web build`.
4. Add or update golden cases for retrieval behavior changes.
5. Include screenshots for interface changes and describe keyboard behavior.

Good first contributions include a new metadata filter, an evaluation failure visualization, a documented corpus adapter, or additional adversarial cases. Never commit model weights, uploaded documents, credentials, or private evaluation data.
