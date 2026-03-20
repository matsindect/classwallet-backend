.PHONY: dev install migrate seed test lint format

install:
	pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload --port 8000

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(msg)"

seed:
	python -m scripts.seed

test:
	pytest -v

lint:
	ruff check app/ tests/
	black --check app/ tests/

format:
	ruff check --fix app/ tests/
	black app/ tests/
