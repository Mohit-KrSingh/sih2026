# EduTrace: Student Data Management and Verification System

A student team project for the Smart India Hackathon AICTE problem statement: managing and verifying student records keyed by the 12-digit APAAR ID.

> **Demo mode notice**: External dependencies (APAAR registry, AICTE master list, OTP delivery, identity verification, and file storage) are simulated in this build. We use mock interfaces for local testing and demo evaluation, with HTTP client stubs set up for real integration.

---

## What it is

Right now, colleges report aggregate student numbers rather than individual student records keyed by APAAR ID. Because of this, AICTE cannot easily catch colleges that admit students beyond their approved intake or find students enrolled in more than one college at the same time.

Our system gives colleges a portal and API to submit student records with their APAAR IDs. Every record runs through an automated validation engine that checks format, age, approved courses, intake quotas, and cross-college duplicates. AICTE gets live dashboards to monitor intake and review exceptions, while employers can verify student credentials only when the student gives consent.

### Core features
- **College data entry**: Manual entry, CSV/XLSX bulk upload, and REST API for campus ERPs.
- **Validation engine**: 34 rules running cheap checks first (file format, APAAR registry check, course limits, duplicates, and anomalies).
- **Exceptions and review**: Colleges can justify real-world anomalies (like court-ordered seats); AICTE officers review and approve or reject them.
- **Live dashboards**: AICTE sees over-intake colleges, duplicate enrolments, and real-time submission feeds via Server-Sent Events.
- **Student consent & verification**: Students approve verification requests on a private portal; verifiers get minimal data with Ed25519 signatures and tamper-evident QR codes.

---

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide icons, ECharts.
- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0.
- **Database & Cache**: PostgreSQL 16, Redis 7.
- **Tools & Libraries**: pandas, RapidFuzz, scikit-learn (IsolationForest), PyNaCl, ReportLab.

---

## How to run it

You can run the full stack using Docker Compose or directly on your machine.

### Option A: With Docker Compose

```bash
# Clone the repository
git clone <repo-url>
cd sih2026

# Copy environment variables
cp .env.example .env

# Start all services
make up
# or: docker compose up -d

# Seed sample colleges, courses, and demo records
make seed

# Check system health
curl http://localhost:8000/api/v1/health

# Stop everything when done
make down
```

### Option B: Local Setup (without Docker)

Prerequisites: Python 3.12, Node.js 20+, PostgreSQL 16, and Redis 7.

```powershell
# Setup Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# Setup frontend dependencies
cd frontend
npm install
cd ..

# Start databases and run migrations
make up
alembic -c backend/alembic.ini upgrade head

# Seed demo data
make seed

# Run backend (port 8000)
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

# Run frontend (port 5173, in a separate terminal)
cd frontend
npm run dev
```

### URLs

- Web Portal: [http://localhost:5173](http://localhost:5173)
- Backend API: [http://localhost:8000](http://localhost:8000)
- API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- Student Portal: [http://localhost:5173/student](http://localhost:5173/student)
- Public Verification: [http://localhost:5173/verify](http://localhost:5173/verify)

---

## Standard Commands

We set up common shortcuts in the Makefile (and matching scripts in `scripts/`):

| Command | What it does |
|---|---|
| `make up` | Starts PostgreSQL 16, Redis 7, backend API, and frontend dev server. |
| `make down` | Stops running services and background jobs. |
| `make test` | Runs the test suite (backend pytest + frontend vitest). |
| `make lint` | Runs code quality checks (ruff on backend, eslint on frontend). |
| `make seed` | Seeds 30 demo colleges, courses, quotas, and test students. |
| `make demo` | Resets the database to a clean demo state with test scenarios ready. |
| `make rules-doc` | Regenerates `docs/RULES.md` from the Python validation rule registry. |

---

## Demo Accounts

All demo accounts use password **`Demo@12345`**.

| Role | Email / Identifier | College / Organization | What you can test |
|---|---|---|---|
| **`aicte_admin`** | `aicte_admin@aicte-india.org` | AICTE Headquarters | Rule tuning, audit log verification, verifier approvals. |
| **`aicte_officer`** | `aicte_officer@aicte-india.org` | AICTE Compliance | Over-intake red list, duplicate cases, anomaly alerts, review queue. |
| **`college_admin`** *(Clean)* | `admin@piaet-pune.edu.in` | Pune Institute of Advanced Engg (`1-10000001`) | Compliant submissions, verified student records, QR certificates. |
| **`college_admin`** *(Exceptions)* | `admin@mmit-mumbai.ac.in` | Mumbai Metropolitan Inst of Tech (`1-10000002`) | Over-intake flag (68/60 seats), cross-college duplicate, review queries. |
| **`college_admin`** *(Draft)* | `admin@ngec-nagpur.gov.in` | Nagpur Govt Engineering College (`1-10000003`) | Live draft mode: seat declarations, student form, bulk CSV upload. |
| **`college_staff`** | `staff@mmit-mumbai.ac.in` | Mumbai Metropolitan Inst of Tech | Staff entry and justifications; blocked from final submission. |
| **`college_viewer`** | `viewer@mmit-mumbai.ac.in` | Mumbai Metropolitan Inst of Tech | Read-only auditor role; cannot edit or upload. |
| **`verifier`** | `verifier@tcs-verifications.com` | TCS Background Checks | Verifier flow: search student, request consent, check minimal record. |
| **Student** *(Valid)* | `111122223333` | Aarav Sharma | Student portal at `/student`: log in with OTP `123456`, approve consent. |
| **Student** *(Duplicate)* | `555566667777` | Priya Patel | Enrolled at both Pune and MMIT; flags cross-college duplicate rule. |

> In demo mode, all OTP verification prompts accept **`123456`**. You can also see outgoing simulated SMS messages at `GET /api/v1/dev/outbox`.

---

## Mock vs Real Interfaces

As required by Hard Rule 5, every external dependency has a clean Python Protocol interface. For local running and hackathon demos, mock classes serve fake data. The real HTTP client classes exist as stubs and raise `NotImplementedError` until production credentials and endpoints are configured.

| Dependency | Interface | Mock class | Real class stub | Setting & Default | Notes |
|---|---|---|---|---|---|
| APAAR Registry | `ApaarClient` | `MockApaarClient` | `HttpApaarClient` | `APAAR_CLIENT_TYPE="mock"` | Mock checks `mock_apaar_registry` table with RapidFuzz name matching. |
| AICTE Master Directory | `AicteMasterClient` | `MockAicteMasterClient` | `HttpAicteMasterClient` | `AICTE_MASTER_CLIENT_TYPE="mock"` | Provides 30 demo colleges across 8 states with approved intakes. |
| OTP / SMS Service | `OtpSender` | `MockOtpSender` | `HttpOtpSender` | `OTP_SENDER_TYPE="mock"` | Saves OTPs to Redis (5 min TTL) and logs them to `dev_outbox`. |
| Signatory Check | `IdentityVerifier` | `MockIdentityVerifier` | `HttpIdentityVerifier` | `IDENTITY_VERIFIER_TYPE="mock"` | Simulates head-of-institution signatory verification during activation. |
| Evidence Storage | `Storage` | `LocalStorage` | `HttpStorage` | `STORAGE_TYPE="mock"` | Stores uploaded justifications and evidence on disk under `uploads/`. |

---

## Known Limitations

We built this for a hackathon demo, so there are a few practical limits:
1. **Mock government APIs**: We do not connect to real APAAR or DigiLocker servers because production credentials are restricted. All registry lookups use seeded test records.
2. **Single-server real-time stream**: The SSE activity feed uses an in-process Redis pub/sub listener. It works well for our demo but would need a message queue cluster for national-scale concurrent traffic.
3. **Synthetic anomaly baseline**: The IsolationForest anomaly detection model is trained on synthetic and historical demo distributions. In a real deployment, AICTE would train it on several years of national admission data.
4. **Local file uploads**: Justification PDFs and evidence files are saved on the local filesystem rather than an S3 bucket or cloud object storage.
5. **No Aadhaar storage**: In strict compliance with DPDP and hackathon rules, we never collect or store Aadhaar numbers.

---

## Documentation Links

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture, sequence diagrams, and validation pipeline.
- [docs/RULES.md](docs/RULES.md) - Validation rules catalogue and severity levels.
- [demo/DEMO.md](demo/DEMO.md) - Step-by-step evaluator click guide for all demo scenarios.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Team & Credits

Built with care for Smart India Hackathon 2026.
Special thanks to AICTE and the Ministry of Education for the problem statement.
