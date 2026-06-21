#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# ResuMesh — Initial Setup Script
# Run once after cloning to prepare the development environment
# ─────────────────────────────────────────────────────────────

set -e
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo "  ⚡ ResuMesh Setup"
echo "  ─────────────────"
echo ""

# ── Check prerequisites ──────────────────────────────────────
command -v docker &>/dev/null || error "Docker is not installed. Please install Docker Desktop."
command -v python3 &>/dev/null || error "Python 3.11+ is required."
command -v node &>/dev/null || error "Node.js 20+ is required."
info "Prerequisites verified"

# ── Environment ──────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    warn ".env created from .env.example. Please set SECRET_KEY, JWT_SECRET_KEY, and choose LLM_PROVIDER."
else
    info ".env already exists"
fi

# ── Directories ──────────────────────────────────────────────
mkdir -p backend/uploads backend/logs data/raw data/processed models/production
touch data/raw/.gitkeep data/processed/.gitkeep
info "Data directories created"

# ── Python dependencies ──────────────────────────────────────
echo ""
echo "  Installing Python dependencies..."
cd backend
pip install -r requirements.txt -q
cd ..
info "Python packages installed"

# ── Node dependencies ────────────────────────────────────────
echo ""
echo "  Installing Node dependencies..."
cd frontend
npm install --legacy-peer-deps --silent
cd ..
info "Node packages installed"

# ── Start infrastructure ─────────────────────────────────────
echo ""
echo "  Starting Docker services..."
docker compose up -d
sleep 5
info "Docker services started"

# ── Database migration ───────────────────────────────────────
echo ""
echo "  Running database migrations..."
cd backend
sleep 3  # Wait for Postgres to be ready
alembic upgrade head 2>/dev/null && info "Database migrated" || warn "Migration failed — DB may not be ready yet. Run: cd backend && alembic upgrade head"
cd ..

# ── ML bootstrap ─────────────────────────────────────────────
echo ""
echo "  Bootstrapping ML pipeline..."
python ml/ingest.py data/raw/feedback.json synthetic 2>/dev/null && \
python ml/parse.py data/raw/feedback.json data/processed/training_data.json 2>/dev/null && \
python ml/train.py data/processed/training_data.json models/match_model.pkl 2>/dev/null && \
info "Initial ML model trained" || warn "ML setup incomplete — run 'make ml-run' manually"

echo ""
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ ResuMesh setup complete!"
echo ""
echo "  Next steps:"
echo "    1. Edit .env — set your LLM API key"
echo "    2. make backend    → http://localhost:8000/docs"
echo "    3. make frontend   → http://localhost:3000"
echo "    4. Load extension from chrome://extensions/ → extension/ dir"
echo ""
echo "  Services:"
echo "    API:      http://localhost:8000"
echo "    Frontend: http://localhost:3000"
echo "    MLflow:   http://localhost:5000"
echo "    Airflow:  http://localhost:8080"
echo "    Grafana:  http://localhost:3001"
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
