.PHONY: install install-dev backend frontend serve test lint clean

# Install all dependencies
install: install-backend install-frontend

install-backend:
	cd backend && pip install -e .

install-dev:
	cd backend && pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

# Development servers
serve: serve-backend

serve-backend:
	cd backend && uvicorn ctm.api.app:create_app --factory --reload --port 8000

serve-frontend:
	cd frontend && npm run dev

# Build
build-frontend:
	cd frontend && npm run build

# Testing
test:
	cd backend && pytest

test-golden:
	cd backend && pytest tests/golden/

# Linting
lint:
	cd backend && ruff check src/ tests/
	cd backend && ruff format --check src/ tests/

format:
	cd backend && ruff format src/ tests/

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.trialibre_cache backend/trialibre.db
