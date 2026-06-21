# ╔══════════════════════════════════════════════════════╗
# ║           ResuMesh — Development Makefile            ║
# ╚══════════════════════════════════════════════════════╝

.PHONY: help dev up down logs backend frontend install test lint migrate \
        ml-run extension-build clean reset

# ── Default ────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  ⚡ ResuMesh Development Commands"
	@echo ""
	@echo "  Infrastructure:"
	@echo "    make up          — Start all Docker services"
	@echo "    make down        — Stop all Docker services"
	@echo "    make logs        — Tail all service logs"
	@echo "    make reset       — Remove volumes and restart fresh"
	@echo ""
	@echo "  Backend:"
	@echo "    make backend     — Run FastAPI dev server (hot reload)"
	@echo "    make migrate     — Run Alembic migrations"
	@echo "    make test        — Run pytest suite"
	@echo "    make lint        — Run ruff + mypy"
	@echo ""
	@echo "  Frontend:"
	@echo "    make frontend    — Start Vite dev server"
	@echo "    make install     — Install all npm dependencies"
	@echo ""
	@echo "  ML:"
	@echo "    make ml-ingest   — Generate training data"
	@echo "    make ml-train    — Train matching model"
	@echo "    make ml-run      — Full ML pipeline (ingest → parse → train → evaluate → register)"
	@echo ""
	@echo "  Extension:"
	@echo "    make extension-build — Package Chrome extension"
	@echo ""

# ── Infrastructure ─────────────────────────────────────────────────────────────
up:
	docker compose up -d
	@echo "✅ Services started. Access:"
	@echo "   API:      http://localhost:8000/docs"
	@echo "   Frontend: http://localhost:3000"
	@echo "   MLflow:   http://localhost:5000"
	@echo "   Grafana:  http://localhost:3001 (admin/admin)"
	@echo "   Airflow:  http://localhost:8080 (airflow/airflow)"

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

reset:
	docker compose down -v
	docker compose up -d

# ── Backend ─────────────────────────────────────────────────────────────────────
backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	cd backend && alembic upgrade head

migrate-down:
	cd backend && alembic downgrade -1

migrate-gen:
	cd backend && alembic revision --autogenerate -m "$(MSG)"

test:
	cd backend && pytest tests/ -v --tb=short

test-cov:
	cd backend && pytest tests/ -v --cov=app --cov-report=html --cov-report=term

lint:
	cd backend && ruff check app/ tests/
	cd backend && ruff format --check app/ tests/

format:
	cd backend && ruff format app/ tests/

# ── Frontend ────────────────────────────────────────────────────────────────────
install:
	cd frontend && npm install

frontend:
	cd frontend && npm run dev

build-frontend:
	cd frontend && npm run build

# ── ML Pipeline ─────────────────────────────────────────────────────────────────
ml-ingest:
	python ml/ingest.py data/raw/feedback.json synthetic

ml-parse:
	python ml/parse.py data/raw/feedback.json data/processed/training_data.json

ml-features:
	python ml/features.py data/processed/training_data.json data/processed/features.npz data/processed/feature_names.json

ml-train:
	python ml/train.py data/processed/training_data.json models/match_model.pkl

ml-evaluate:
	python ml/evaluate.py models/match_model.pkl data/processed/training_data.json ml/evaluation_report.json

ml-register:
	python ml/register.py models/match_model.pkl ml/evaluation_report.json

ml-run: ml-ingest ml-parse ml-features ml-train ml-evaluate ml-register
	@echo "✅ Full ML pipeline completed"

ml-dvc:
	dvc repro

# ── Extension ───────────────────────────────────────────────────────────────────
extension-build:
	@mkdir -p extension/dist
	@cp -r extension/manifest.json extension/popup.html extension/src extension/dist/ 2>/dev/null || true
	@echo "✅ Extension ready to load from extension/dist/"

# ── Setup ────────────────────────────────────────────────────────────────────────
setup: install
	@cp -n .env.example .env 2>/dev/null || true
	@mkdir -p backend/uploads backend/logs data/raw data/processed models/production
	@echo "✅ Project setup complete. Edit .env then run: make up"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	rm -rf backend/htmlcov frontend/dist frontend/node_modules/.cache
	@echo "✅ Cleaned up"
