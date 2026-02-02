# PatentAI 🔍

AI-powered patent infringement detection system with hybrid search and LLM analysis.

> **Vibe Coding Full-Stack Project** - Clean architecture, modern stack, production-ready.

## Features

- 🔍 **Hybrid Search** - Vector similarity (pgvector) + fuzzy text matching (RapidFuzz)
- 🤖 **LLM Analysis** - AI-powered infringement risk assessment with explanations
- 📊 **Prometheus Metrics** - Full observability with Grafana dashboards
- ⚡ **Redis Caching** - Fast repeated queries
- 🎨 **Modern UI** - React + Vite + TailwindCSS

## Tech Stack

### Backend
- **FastAPI** - High-performance async API
- **PostgreSQL + pgvector** - Vector similarity search
- **SQLAlchemy** - Async ORM
- **Redis** - Caching layer
- **Celery** - Background tasks (optional)

### AI/ML
- **Ollama** - Local embeddings (nomic-embed-text, 768-dim)
- **OpenRouter** - LLM API (GPT-4o-mini)
- **RapidFuzz** - Fuzzy string matching

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **React Query** - Data fetching
- **Recharts** - Charts

### Monitoring
- **Prometheus** - Metrics collection
- **Grafana** - Dashboards
- **prometheus-fastapi-instrumentator** - Auto HTTP metrics

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Ollama with `nomic-embed-text` model
- OpenRouter API key

### 1. Clone and configure
```bash
cd patentAI
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY
```

### 2. Start services
```bash
docker-compose up -d
```

### 3. Access
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)

## Development

### Backend only
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend only
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/patents/` | Upload a new patent |
| GET | `/patents/{id}` | Get patent by ID |
| GET | `/patents/` | List all patents |
| POST | `/patents/search` | Hybrid search |
| POST | `/patents/compare` | Compare two patents |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      React Frontend                          │
│  Search │ Upload │ Compare │ Dashboard                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│  /patents │ /search │ /compare │ /health │ /metrics         │
└─────────────────────────────────────────────────────────────┘
        │              │                │
        ▼              ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   pgvector   │ │    Redis     │ │  Prometheus  │
│ (embeddings) │ │   (cache)    │ │ (monitoring) │
└──────────────┘ └──────────────┘ └──────────────┘
        │
        ▼
┌──────────────────────────────────────┐
│     Ollama (local) │ OpenRouter      │
│     Embeddings     │ LLM Analysis    │
└──────────────────────────────────────┘
```

## Project Structure

```
patentAI/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Config, database
│   │   ├── models/       # SQLAlchemy models
│   │   └── services/     # Business logic
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # Reusable components
│   │   ├── pages/        # Route pages
│   │   ├── hooks/        # Custom hooks
│   │   └── lib/          # Utilities
│   ├── Dockerfile
│   └── package.json
├── monitoring/
│   └── prometheus.yml
├── docker-compose.yml
└── README.md
```

## License

MIT

---

Built with 💜 by Dragon & Mia
