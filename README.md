# 🚀 ResuMesh — AI-Powered Job Application Copilot

[![CI/CD](https://github.com/yourusername/resumesh/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/resumesh/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18+-61DAFB.svg)](https://reactjs.org/)

> ResuMesh is an AI-powered job application copilot that automatically analyzes job descriptions, scores your resume, identifies skill gaps, and generates tailored cover letters — all within your browser.

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Chrome Extension](#chrome-extension)
- [API Documentation](#api-documentation)
- [ML Pipeline](#ml-pipeline)
- [MLOps](#mlops)
- [Monitoring](#monitoring)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## ✨ Features

### Core Features
- 🔍 **Automatic Job Detection** — Detects job postings on LinkedIn, Wellfound, Internshala, Naukri
- 📊 **Resume Match Scoring** — AI-powered compatibility scoring (0–100)
- 🎯 **Skill Gap Analysis** — Identifies missing skills with priority rankings
- ✉️ **Cover Letter Generator** — Tailored cover letters using RAG
- 🤖 **Career Coach** — Conversational AI assistant powered by LangGraph
- 📈 **Application Tracker** — Full pipeline tracking with analytics
- 🔄 **Feedback Loop** — Continuously improves through user feedback

### Technical Features
- JWT Authentication with refresh tokens
- Role-Based Access Control (RBAC)
- Vector search with ChromaDB
- MLflow experiment tracking
- Airflow pipeline orchestration
- Prometheus + Grafana monitoring
- DVC data versioning
- Docker Compose deployment

---

## 🏗️ Architecture

```
resumesh/
├── frontend/          # React + TypeScript + TailwindCSS SaaS Dashboard
├── extension/         # Chrome Extension (Manifest V3)
├── backend/           # FastAPI REST API
├── ml/                # ML training pipelines
├── airflow/           # Apache Airflow DAGs
├── monitoring/        # Prometheus + Grafana configs
├── docker/            # Dockerfiles
├── docs/              # Documentation
├── tests/             # Test suites
├── .github/           # CI/CD workflows
├── infrastructure/    # Infrastructure as Code
├── scripts/           # Utility scripts
├── data/              # Data (DVC tracked)
├── models/            # Model artifacts (DVC tracked)
└── logs/              # Application logs
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, TailwindCSS, Vite |
| Extension | Chrome MV3, React, TypeScript |
| Backend | Python 3.11, FastAPI, SQLAlchemy |
| Database | PostgreSQL 15 |
| Vector DB | ChromaDB |
| Auth | JWT, bcrypt |
| ML | Scikit-Learn, Sentence Transformers |
| RAG | LangChain, LangGraph |
| MLOps | MLflow, DVC, Apache Airflow |
| Monitoring | Prometheus, Grafana |
| Containers | Docker, Docker Compose |
| CI/CD | GitHub Actions |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+
- Python 3.11+
- Git

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/resumesh.git
cd resumesh
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Start All Services
```bash
docker-compose up -d
```

### 4. Access Services
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| MLflow | http://localhost:5000 |
| Airflow | http://localhost:8080 |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |

---

## 💻 Development Setup

See [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) for detailed setup instructions.

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Extension
cd extension
npm install
npm run dev
```

---

## 🔌 Chrome Extension

1. Navigate to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `extension/dist/` folder

Supported job portals:
- LinkedIn Jobs
- Wellfound (AngelList)
- Internshala
- Naukri

---

## 📚 API Documentation

Full API docs available at `http://localhost:8000/docs` (Swagger UI)

Key endpoints:
- `POST /api/v1/auth/register` — Register user
- `POST /api/v1/auth/login` — Login
- `POST /api/v1/resumes/upload` — Upload resume
- `POST /api/v1/jobs/analyze` — Analyze job description
- `GET /api/v1/matching/score` — Get match score
- `POST /api/v1/coverletters/generate` — Generate cover letter
- `POST /api/v1/rag/chat` — Chat with career coach

---

## 🤖 ML Pipeline

See [docs/MLOPS_GUIDE.md](docs/MLOPS_GUIDE.md) for full details.

```bash
# Run DVC pipeline
dvc repro

# View experiments in MLflow
mlflow ui --port 5000
```

---

## 📊 MLOps

- **Experiment Tracking**: MLflow at `localhost:5000`
- **Data Versioning**: DVC with remote storage
- **Orchestration**: Apache Airflow at `localhost:8080`
- **Model Registry**: MLflow Model Registry

---

## 📈 Monitoring

- **Metrics**: Prometheus at `localhost:9090`
- **Dashboards**: Grafana at `localhost:3001` (admin/admin)
- **Alerts**: Configured alert rules in `monitoring/alerts/`

---

## 🧪 Testing

```bash
# Backend tests
cd backend && pytest tests/ -v --cov=app

# Frontend tests
cd frontend && npm test

# Extension tests
cd extension && npm test
```

---

## 🚢 Deployment

See [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)

```bash
# Production build
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 License

MIT License — see [LICENSE](LICENSE)
