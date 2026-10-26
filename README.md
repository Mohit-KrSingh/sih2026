# APAAR Student Data Management and Verification System

An AICTE platform for automated APAAR-based student data validation, intake compliance monitoring, duplicate enrolment prevention, and secure stakeholder verification.

> **Demo mode notice**: External dependencies (APAAR registry, AICTE master directory, OTP/SMS delivery, DigiLocker identity verification) are currently simulated for demonstration and development purposes.

---

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2 (sync), Alembic, Pydantic v2, PostgreSQL 16, Redis 7
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, TanStack Query/Table, ECharts
- **Testing**: pytest (backend), Vitest (frontend)
- **Containerization**: Docker Compose (`db`, `redis`, `backend`, `frontend`)

---

## Quickstart

### Prerequisites
- Docker Compose **or** local PostgreSQL 16 + Redis 7 + Node.js 20+ + Python 3.12
- Make (`GNU Make`)

### Run the Stack
```bash
# Start all services (Database, Redis, FastAPI Backend, React Frontend)
make up

# Check status
curl http://localhost:8000/api/v1/health

# Stop all services
make down
```

### Run Tests and Linters
```bash
# Run backend pytest and frontend vitest
make test

# Run backend ruff and frontend eslint
make lint
```

### URLs
- **Frontend UI**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## Standard Commands
- `make up` - Start containers or local services
- `make down` - Stop all services
- `make test` - Run full test suite (pytest + vitest)
- `make lint` - Run code quality checks (ruff + eslint)
- `make seed` - Populate sample institutions, courses, and demo data
- `make demo` - Reset environment to scripted demo state
- `make rules-doc` - Generate rule catalogue documentation
