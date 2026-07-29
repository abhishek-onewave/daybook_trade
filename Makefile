SHELL := /bin/bash
PYTHON := .venv/bin/python
UVICORN := .venv/bin/uvicorn
ALEMBIC := .venv/bin/alembic

.PHONY: setup migrate backend frontend dev test guard

setup:
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r backend/requirements.txt
	cd frontend && npm install

migrate:
	$(ALEMBIC) -c backend/alembic.ini upgrade head

backend: migrate
	$(UVICORN) backend.app.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm run dev

dev:
	@bash scripts/dev.sh

test: migrate
	$(PYTHON) -m pytest backend/tests
	cd frontend && npm run lint

guard:
	$(PYTHON) -m pytest backend/tests/test_read_only_guard.py
	.venv/bin/ruff check backend
	cd frontend && npm run lint

