.PHONY: local_test local_up local_ci lint

LOCAL_ENV ?= .env.local

local_up:
	docker compose up -d db redis worker

local_down:
	docker compose down

local_test:
	@echo "Run pytest"
	ENV_FILE=$(LOCAL_ENV) uv run pytest -q

lint:
	@echo "Run mypy"
	uv run mypy .

local_ci: lint local_test
	@echo "Local ci success"
