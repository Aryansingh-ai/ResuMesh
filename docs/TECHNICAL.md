# ResuMesh — Full Documentation

## Table of Contents
1. [Architecture Overview](#architecture)
2. [Local Development Setup](#local-setup)
3. [Backend API Reference](#api-reference)
4. [Chrome Extension Guide](#chrome-extension)
5. [ML Pipeline](#ml-pipeline)
6. [MLOps & Monitoring](#mlops)
7. [Deployment](#deployment)

---

## Architecture Overview <a name="architecture"></a>

```
┌─────────────────────────────────────────────────────────┐
│                    ResuMesh Platform                    │
├───────────┬──────────────┬───────────────┬──────────────┤
│  Chrome   │   React      │  FastAPI      │  ML Pipeline │
│ Extension │  Dashboard   │  Backend      │  (DVC+MLflow)│
│           │  (Vite+TS)   │  (Python 3.11)│              │
└─────┬─────┴──────┬───────┴──────┬────────┴──────┬───────┘
      │            │              │               │
      └────────────┴──────────────┘               │
                        │                         │
              ┌─────────▼─────────┐               │
              │   PostgreSQL 16   │◄──────────────┘
              │   Redis Cache     │
              │   ChromaDB        │
              └───────────────────┘
```

### Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend | FastAPI + SQLAlchemy | REST API, auth, business logic |
| Frontend | React 18 + TypeScript + Tailwind | SaaS dashboard |
| Extension | Chrome MV3 | Job scraping, instant analysis |
| Vector DB | ChromaDB | Resume/job semantic search |
| LLM | Ollama / Groq / Gemini | Cover letters, RAG coaching |
| ML Pipeline | scikit-learn + MLflow + DVC | Match model training |
| Orchestration | Apache Airflow | Scheduled pipelines |
| Monitoring | Prometheus + Grafana | Metrics & alerting |

---

## Local Development Setup <a name="local-setup"></a>

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- Chrome browser (for extension)

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/resumesh.git
cd resumesh

# Copy and edit environment variables
cp .env.example .env
# Edit .env: set JWT_SECRET_KEY, choose LLM_PROVIDER, etc.
```

### 2. Start Infrastructure

```bash
# Start all services (Postgres, Redis, ChromaDB, MLflow, Airflow, etc.)
make up

# Verify they're running
docker compose ps
```

### 3. Run Database Migrations

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

### 4. Start the Backend

```bash
# From backend/
make backend
# → http://localhost:8000/docs (Swagger UI)
```

### 5. Start the Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 6. Install Chrome Extension

1. Open `chrome://extensions/`
2. Enable **Developer Mode**
3. Click **Load unpacked**
4. Select the `extension/` folder
5. Navigate to a job on LinkedIn/Wellfound/Internshala/Naukri

---

## Backend API Reference <a name="api-reference"></a>

All endpoints are prefixed with `/api/v1`.

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get JWT tokens |
| POST | `/auth/refresh` | Refresh access token |
| GET | `/auth/me` | Get current user |

### Resumes
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/resumes/upload` | Upload PDF/DOCX |
| GET | `/resumes/` | List all resumes |
| DELETE | `/resumes/{id}` | Delete resume |

### Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/jobs/analyze` | Submit job for analysis |
| GET | `/jobs/` | List analyzed jobs |
| GET | `/jobs/{id}` | Get full job details |

### Matching
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/matching/score` | Compute match score |
| POST | `/matching/quick-score` | Quick in-memory score |

### Cover Letters
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/coverletters/generate` | Generate cover letter |
| GET | `/coverletters/` | List saved letters |

### RAG Coach
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/rag/chat` | Chat with AI career coach |

### Applications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/applications/` | List all applications |
| PATCH | `/applications/{id}/status` | Update status |
| GET | `/applications/stats/summary` | Pipeline stats |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/analytics/dashboard` | Dashboard metrics |

---

## Chrome Extension Guide <a name="chrome-extension"></a>

### Supported Job Portals

| Portal | Trigger | UI Style |
|--------|---------|----------|
| **LinkedIn** | `/jobs/view/` pages | Full sidebar (340px) |
| **Wellfound** | `/jobs/` pages | Floating overlay card |
| **Internshala** | `/internship/` pages | Inline widget |
| **Naukri** | `/job-listings/` pages | Slide-in sidebar with toggle |

### Flow
1. Extension detects job page via URL pattern
2. Content script extracts job title, company, description
3. Background service worker sends to `/api/v1/matching/quick-score`
4. UI shows match %, matched skills, missing skills
5. User can save job, generate cover letter, or open AI coach

---

## ML Pipeline <a name="ml-pipeline"></a>

### Running the Full Pipeline

```bash
# Option 1: Using Makefile
make ml-run

# Option 2: Step by step
python ml/ingest.py data/raw/feedback.json synthetic  # Generate data
python ml/parse.py data/raw/feedback.json data/processed/training_data.json
python ml/train.py data/processed/training_data.json models/match_model.pkl
python ml/evaluate.py models/match_model.pkl data/processed/training_data.json
python ml/register.py models/match_model.pkl

# Option 3: DVC
dvc repro
```

### Models Trained

| Model | Features |
|-------|---------|
| Logistic Regression | Baseline, fast |
| Random Forest (100 trees) | Good generalization |
| Gradient Boosting | Best accuracy |

### Feature Engineering (9 features)

| Feature | Description |
|---------|-------------|
| `skill_overlap_ratio` | % of required skills in resume |
| `preferred_skill_overlap_ratio` | % of preferred skills matched |
| `experience_ratio` | Resume years / required years (capped at 2) |
| `education_score` | Education level match score |
| `tech_stack_coverage` | % of tech stack covered |
| `has_certifications` | Binary flag |
| `seniority_score` | Normalized seniority level |
| `n_required_skills` | Count of required skills |
| `n_resume_skills` | Count of resume skills |

### Quality Gates (for auto-promotion)
- F1 Score ≥ 0.75
- ROC-AUC ≥ 0.75
- Accuracy ≥ 0.72

---

## MLOps & Monitoring <a name="mlops"></a>

### Airflow DAGs

| DAG | Schedule | Purpose |
|-----|----------|---------|
| `resume_processing_pipeline` | Every 30 min | Parse + embed new resumes |
| `model_retraining_pipeline` | Daily 2 AM | Retrain model from feedback |

Access Airflow at `http://localhost:8080` (airflow/airflow)

### Prometheus Metrics (custom)
- `resumesh_resume_uploads_total` — uploads by status
- `resumesh_match_requests_total` — matches by model_version
- `resumesh_rag_queries_total` — RAG queries
- `resumesh_feedback_collected_total` — feedback by type

### Grafana
Access at `http://localhost:3001` (admin/admin)

Dashboards auto-provisioned from `monitoring/grafana/dashboards/`

---

## Deployment <a name="deployment"></a>

### Docker (Self-hosted)

```bash
# Build images
docker build -f docker/Dockerfile.backend -t resumesh-backend ./backend
docker build -f docker/Dockerfile.frontend -t resumesh-frontend ./frontend

# Start everything
docker compose -f docker-compose.yml up -d
```

### Environment Variables for Production

```env
APP_ENV=production
DEBUG=false
JWT_SECRET_KEY=<strong-random-key>
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/resumesh
ALLOWED_ORIGINS=https://yourdomain.com
LLM_PROVIDER=groq
GROQ_API_KEY=<your-key>
```

### CI/CD (GitHub Actions)

The `.github/workflows/ci.yml` automatically:
1. Runs backend tests (pytest) on every PR
2. Runs frontend lint + build
3. Builds and pushes Docker images to GHCR on `main` merge
4. Runs security scanning (bandit + safety)
