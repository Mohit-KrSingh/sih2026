# APAAR Student Data Management and Verification System

An AICTE platform for automated APAAR-based student data validation, intake compliance monitoring, duplicate enrolment prevention, and secure stakeholder verification.

> **Demo mode notice**: External dependencies (APAAR identity registry, AICTE master directory, OTP/SMS delivery, DigiLocker identity verification, and cloud object storage) are currently simulated for demonstration and development purposes. Mock interfaces provide realistic responses while production HTTP client implementations sit behind standardized interfaces as explicit stubs.

---

## 1. System Overview

The APAAR Student Data Management and Verification System addresses a critical gap in technical education oversight: today, most colleges report aggregate student numbers rather than individual student records keyed by the national 12-digit **Automated Permanent Academic Account Registry (APAAR)** ID. This prevents the All India Council for Technical Education (AICTE) from detecting admissions beyond approved intake quotas or identifying students concurrently enrolled in multiple institutions.

This platform provides an end-to-end statutory data management pipeline:
1. **Institution Data Ingestion**: Seat declarations, single-student entry, and bulk CSV/XLSX uploads.
2. **Automated Validation Engine**: Real-time evaluation of 34 pure validation rules (file format, APAAR registry match, age bands, course approval, intake quotas, and cross-college duplicates).
3. **Regulatory Review Workflow**: Institutional exception justifications, AICTE review queue, interactive query round-trips, and post-lock change requests.
4. **Central Repository**: Immutable locked student records, Fernet-encrypted Date of Birth (DOB) at rest, and SHA-256 hash-chained audit logging.
5. **Intelligent Anomaly Detection**: Statistical quota outlier alerts and unsupervised Machine Learning (`IsolationForest`) anomaly scoring.
6. **Real-Time Monitoring**: Live AICTE executive dashboards with Server-Sent Events (SSE) streaming and statutory multi-format reporting (CSV, XLSX, PDF).
7. **DPDP-Compliant Verification**: Ed25519 cryptographic signatures, tamper-proof QR degree certificates, and 24-hour single-use student consent workflows.

---

## 2. Tech Stack

| Layer | Component | Description |
|---|---|---|
| **Frontend** | React 18 + TypeScript + Vite | Tailwind CSS, Radix UI primitives, Lucide icons, React Router v6 |
| **State & Data** | TanStack Query & TanStack Table | Optimistic UI updates, server cache invalidation, paginated data grids |
| **Visualizations** | Apache ECharts (`echarts-for-react`) | Geographic state maps, intake vs enrolment bars, live anomaly charts |
| **Backend API** | Python 3.12 + FastAPI | Pydantic v2 schemas, strict CORS, custom security & size limiting middleware |
| **ORM & Database** | SQLAlchemy 2.0 (sync) + PostgreSQL 16 | 26 relational tables, compound index optimization, Alembic migrations |
| **Cache & Realtime** | Redis 7 | OTP storage (5-min TTL), sliding-window rate limiters, SSE Pub/Sub broker |
| **Validation & ML** | pandas, RapidFuzz, scikit-learn | Cheap-checks-first hierarchy, fuzzy name matching, `IsolationForest` outliers |
| **Cryptographic Proofs** | PyNaCl (libsodium) + cryptography | Ed25519 digital signatures, Fernet symmetric DOB encryption at rest |
| **Documents & Reports** | reportlab + openpyxl + qrcode | Degree certificate PDFs, XLSX compliance workbooks, tamper-proof QR codes |
| **Testing** | pytest + Vitest + Playwright | 450+ backend tests, 100+ frontend tests, end-to-end golden path suite |

---

## 3. Quickstart & Run Steps

The platform supports running via **Docker Compose** (recommended for containerized deployment) or **Local Native Services** (Windows / Linux / macOS).

### 3.1 Prerequisites
- **Git**
- **Docker & Docker Compose** (for Docker deployment)
- **Local Native Environment** (if running without Docker):
  - Python 3.12+
  - Node.js 20+ and npm
  - PostgreSQL 16 (running on port `5432` with user `apaar` / password `apaar`)
  - Redis 7 (running on port `6379`)
  - Make (`GNU Make`) or PowerShell

---

### 3.2 Running with Docker Compose

```bash
# 1. Clone repository
git clone <repo-url>
cd sih2026

# 2. Configure environment variables
cp .env.example .env

# 3. Start all services in background
make up
# or: docker compose up -d

# 4. Populate sample institutions and demo data
make seed

# 5. Verify system health
curl http://localhost:8000/api/v1/health

# 6. Stop all services when finished
make down
# or: docker compose down
```

---

### 3.3 Running Locally (Native Environment)

If running directly on your host machine without Docker:

```powershell
# Windows (PowerShell)
# 1. Setup virtual environment and dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# 2. Setup frontend dependencies
cd frontend
npm install
cd ..

# 3. Start local PostgreSQL and Redis services (or use make up)
make up

# 4. Run database migrations
$env:PYTHONPATH = "backend"
.\.venv\Scripts\alembic -c backend/alembic.ini upgrade head

# 5. Deterministically seed demo institutions, courses, and accounts
make seed

# 6. Run Backend server (port 8000)
.\.venv\Scripts\uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

# 7. Run Frontend Vite server (port 5173, separate terminal)
cd frontend
npm run dev
```

---

### 3.4 System URLs

| Service / Interface | URL | Purpose |
|---|---|---|
| **Frontend Web Portal** | [http://localhost:5173](http://localhost:5173) | Main application UI (College, AICTE, Verification, Student) |
| **Backend REST API** | [http://localhost:8000](http://localhost:8000) | FastAPI application root |
| **Interactive API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive OpenAPI 3.1 documentation and schema test runner |
| **Alternative API Docs (ReDoc)** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Clean, searchable reference documentation |
| **System Health Endpoint** | [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) | Live DB, Redis, and demo mode health check |
| **Student Consent Portal** | [http://localhost:5173/student](http://localhost:5173/student) | Student self-service DPDP consent approval interface |
| **Public Verification Portal** | [http://localhost:5173/verify](http://localhost:5173/verify) | Employer and regulator degree/enrolment verification |

---

## 4. Standard Commands Reference

All standard lifecycle operations are automated via the project `Makefile` (and matching scripts in `scripts/`):

| Command | Script (Windows / Linux) | Action & Description |
|---|---|---|
| `make up` | `.\scripts\up.ps1` / `./scripts/up.sh` | Starts all services (PostgreSQL 16, Redis 7, Backend API, Frontend UI). |
| `make down` | `.\scripts\down.ps1` / `./scripts/down.sh` | Stops all running stack services and daemons safely. |
| `make test` | `.\scripts\test.ps1` / `./scripts/test.sh` | Executes full test suite (backend `pytest` + frontend `vitest`). |
| `make lint` | `.\scripts\lint.ps1` / `./scripts/lint.sh` | Executes static code analysis (`ruff` on backend, `eslint` on frontend). |
| `make seed` | `.\scripts\seed.ps1` / `./scripts/seed.sh` | Seeds 30 colleges, courses, quotas, 9,200+ mock APAAR IDs, and demo CSVs. |
| `make demo` | `.\scripts\demo.ps1` / `./scripts/demo.sh` | Deterministic reset (`TRUNCATE CASCADE`), Redis flush, re-seed, tamper fixtures. |
| `make rules-doc` | `.\scripts\rules_doc.ps1` / `./scripts/rules_doc.sh` | Generates `docs/RULES.md` markdown catalogue from Python rule registry. |

### Running End-to-End Tests
```bash
# Run Playwright end-to-end browser tests
cd frontend
npx playwright test
```

---

## 5. Demo Accounts & Seeded Scenarios

All demo accounts share the uniform evaluation password: **`Demo@12345`**.

| Role | Email / Identifier | Associated Institution / Entity | Hackathon Scenario & Purpose |
|---|---|---|---|
| **`aicte_admin`** | `aicte_admin@aicte-india.org` | AICTE Headquarters (National Admin) | Rule config tuning, SHA-256 audit chain verification, verifier approvals, full platform governance. |
| **`aicte_officer`** | `aicte_officer@aicte-india.org` | AICTE Compliance & Review Division | Exception review queue, institution query workflows, intake quota adjustments, anomaly oversight. |
| **`college_admin`** *(Stage 1: Clean)* | `admin@piaet-pune.edu.in` | Pune Institute of Advanced Engg & Tech (`1-10000001`) | Compliant admissions, verified central records, Ed25519 signature credentials, tamper-evident QR proofs. |
| **`college_admin`** *(Stage 2: Exceptions)* | `admin@mmit-mumbai.ac.in` | Mumbai Metropolitan Institute of Tech (`1-10000002`) | Over-intake quota exception (68 regular vs 60 approved), cross-college duplicate enrolment with Pune, review queries. |
| **`college_admin`** *(Stage 3: Draft)* | `admin@ngec-nagpur.gov.in` | Nagpur Government Engineering College (`1-10000003`) | Active drafting stage: declare course seat capacity, single student form, bulk CSV ingestion (`demo/messy_upload.csv`). |
| **`college_staff`** | `staff@mmit-mumbai.ac.in` | Mumbai Metropolitan Institute of Tech (`1-10000002`) | Admission staff account: can edit drafts and attach justifications; blocked with HTTP 403 on final submission gate. |
| **`college_viewer`** | `viewer@mmit-mumbai.ac.in` | Mumbai Metropolitan Institute of Tech (`1-10000002`) | Read-only compliance auditor: full viewing privileges; all mutation and upload actions blocked with HTTP 403. |
| **`verifier`** | `verifier@tcs-verifications.com` | Tata Consultancy Services (Background Checks) | Registered prospective employer: requests student consent, conducts single-use academic verification with zero PII exposure. |
| **Student** *(Valid)* | APAAR ID `111122223333` | Aarav Sharma (B.Tech Computer Engg) | Log in at `/student` via mock OTP (`123456`), inspect enrolled institutions, approve/deny employer consent requests. |
| **Student** *(Duplicate)* | APAAR ID `555566667777` | Priya Patel (Dual Enrolment) | Active student concurrently enrolled in both Pune Institute and MMIT Mumbai, demonstrating cross-college duplicate alerts. |

> [!TIP]
> **Mock OTP Code**: All OTP verification screens accept **`123456`** in demo mode, or inspect the simulated notifications at `GET /api/v1/dev/outbox`.

---

## 6. Integration Architecture: Mock vs Real Interfaces

Per **SPEC.md Section 2 (Hard Rule 5)** and **Section 18**, every external dependency sits behind a standardized Python `Protocol` interface. In demo mode, fully functional mock implementations provide deterministic evaluation data. Production HTTP implementations are structured client stubs that raise `NotImplementedError` with clear configuration guidance.

| External Dependency | Protocol Interface | Mock Implementation | Real Implementation Stub | Config Flag & Default | Real-World Counterpart |
|---|---|---|---|---|---|
| **APAAR Identity Registry** | `ApaarClient` (`backend/app/integrations/interfaces.py`) | `MockApaarClient` (`mock/apaar.py`): Batched lookups from `mock_apaar_registry` table (9,214 identities), RapidFuzz fuzzy name comparison. | `HttpApaarClient` (`http/apaar.py`): Raises `NotImplementedError`. | `APAAR_CLIENT_TYPE="mock"` | National Academic Depository (NAD) / Digilocker APAAR API |
| **AICTE Master Directory** | `AicteMasterClient` (`backend/app/integrations/interfaces.py`) | `MockAicteMasterClient` (`mock/aicte_master.py`): 30 realistic institutions across 8 states, course intakes, active/suspended states. | `HttpAicteMasterClient` (`http/aicte_master.py`): Raises `NotImplementedError`. | `AICTE_MASTER_CLIENT_TYPE="mock"` | AICTE National Portal Master Database & Approval APIs |
| **OTP & SMS Gateway** | `OtpSender` (`backend/app/integrations/interfaces.py`) | `MockOtpSender` (`mock/otp.py`): Persists OTPs to Redis (5-min TTL) and logs messages to `dev_outbox` table. | `HttpOtpSender` (`http/otp.py`): Raises `NotImplementedError`. | `OTP_SENDER_TYPE="mock"` | CDAC / NIC National SMS Gateway / Govt Email Gateway |
| **Signatory Identity Check** | `IdentityVerifier` (`backend/app/integrations/interfaces.py`) | `MockIdentityVerifier` (`mock/identity.py`): Validates college head names against official records with simulated biometric checks. | `HttpIdentityVerifier` (`http/identity.py`): Raises `NotImplementedError`. | `IDENTITY_VERIFIER_TYPE="mock"` | DigiLocker e-Sign / Aadhaar e-KYC Identity Service |
| **Document & Evidence Storage** | `Storage` (`backend/app/integrations/interfaces.py`) | `LocalStorage` (`mock/storage.py`): Atomic local filesystem storage under `uploads/` with SHA-256 content-addressable paths. | `HttpStorage` (`http/storage.py`): Raises `NotImplementedError`. | `STORAGE_TYPE="mock"` | Amazon S3 / MinIO S3-Compatible Cloud Storage |

---

## 7. REST API Overview

The backend exposes a secure REST API under `/api/v1` adhering to deny-by-default role-based access control (RBAC).

### 7.1 Authentication Protocols
- **Web UI & Direct Calls**: Bearer JWT tokens passed in `Authorization: Bearer <token>` header. Obtained via `POST /api/v1/auth/login`. Two-factor authentication (MFA) requires completing TOTP/OTP challenge via `POST /api/v1/auth/mfa/verify`.
- **High-Throughput ERP Integration**: API keys passed in `X-API-Key: <key>` header with optional `Idempotency-Key: <uuid>` for safe retries without duplicate student creation.

### 7.2 API Router Modules

| Module / Prefix | Key Endpoints | RBAC Roles | Description |
|---|---|---|---|
| `/api/v1/health` | `GET /health` | Public | System status, PostgreSQL/Redis connectivity, demo mode state. |
| `/api/v1/privacy` | `GET /privacy` | Public | DPDP statutory compliance specs, data minimisation schema, DPO details. |
| `/api/v1/dev` | `GET /dev/outbox` | Public (Dev mode) | Simulated SMS/OTP outbox inspection for demonstration. |
| `/api/v1/auth` | `POST /login`, `POST /refresh`, `POST /mfa/verify`, `GET /me`, `POST /logout` | Public & Authenticated | Argon2id login, JWT token rotation, TOTP/SMS MFA challenge-response. |
| `/api/v1/college/api-keys` | `GET /`, `POST /`, `DELETE /{id}` | `college_admin` | Manage scoped integration API keys (hashed with SHA-256). |
| `/api/v1/institutions` | `GET /{id}`, `GET /{id}/courses`, `GET /{id}/intake-history`, `POST /activation/claim` | Authenticated / Scoped | Institution profiles, approved courses, intake history, activation wizard. |
| `/api/v1/students` | `GET /`, `POST /`, `PUT /{id}`, `DELETE /{id}`, `POST /upload`, `POST /seat-declarations` | College Roles | Seat declarations, student CRUD, bulk CSV upload, autosaved drafts. |
| `/api/v1/submissions` | `GET /`, `POST /{id}/validate`, `POST /{id}/submit`, `POST /{id}/justifications` | `college_admin`, `college_staff` | Run validation engine, attach justifications, submit gate with OTP. |
| `/api/v1/review` | `GET /`, `POST /{id}/decision`, `POST /{id}/queries` | `aicte_officer`, `aicte_admin` | AICTE exception review queue, query issuance, approvals, escalations. |
| `/api/v1/college/queries` | `GET /`, `POST /{id}/respond` | `college_admin`, `college_staff` | Review and respond to official AICTE queries on flagged records. |
| `/api/v1/college/change-requests` | `GET /`, `POST /` | `college_admin` | Post-lock student change requests (e.g. transfers, withdrawals). |
| `/api/v1/aicte/change-requests` | `GET /`, `POST /{id}/decision` | `aicte_officer`, `aicte_admin` | AICTE review and approval/rejection of post-lock change requests. |
| `/api/v1/analytics` | `GET /overview`, `GET /by-state`, `GET /compliance`, `GET /duplicates`, `GET /anomalies`, `GET /stream` | AICTE Roles | AICTE executive dashboard aggregates, over-intake red list, live SSE stream. |
| `/api/v1/verification` | `GET /verify`, `GET /qr/{vid}`, `POST /onboard`, `POST /consent/request`, `POST /consent/{id}/decide`, `GET /consented-record/{id}` | Verifier, Student, Public | Public QR verification, verifier onboarding, student DPDP consent engine. |
| `/api/v1/reports` | `GET /{report_type}` | `aicte_officer`, `aicte_admin` | Download compliance exports in CSV, XLSX, and PDF formats. |
| `/api/v1/institution/reports` | `GET /{report_type}` | `college_admin`, `college_viewer` | Institutional compliance reports scoped strictly to caller's college. |
| `/api/v1/audit` | `GET /`, `GET /verify-chain` | `aicte_admin` | Append-only audit log inspection and SHA-256 chain verification. |
| `/api/v1/rules` | `GET /`, `PUT /{rule_code}` | `aicte_admin` | Dynamic tuning of validation rule levels, parameters, and status. |
| `/api/v1/integration` | `POST /students/bulk` | API Key (`students:write`) | High-throughput JSON ERP student ingestion with idempotency caching. |

---

## 8. Documentation Index

- [docs/PS_COVERAGE.md](docs/PS_COVERAGE.md) - Problem Statement Coverage Audit proving all 10 SIH requirements and 10 Hard Rules with automated tests and demo steps.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Complete system architecture, component topology, sequence diagrams, IsolationForest ML anomaly model, and DPDP privacy specifications.
- [docs/RULES.md](docs/RULES.md) - Comprehensive validation rule catalogue detailing all 34 pure functions, execution scopes, default severity levels, and configurable parameters.
- [demo/DEMO.md](demo/DEMO.md) - Step-by-step evaluator click guide covering all 6 mandatory judging scenarios (over-intake, duplicates, anomalies, live stream, student consent, and tamper detection).
- [docs/DEPENDENCY_AUDIT.md](docs/DEPENDENCY_AUDIT.md) - Security audit of third-party backend and frontend dependencies.
- [SPEC.md](SPEC.md) - Comprehensive system functional and technical specifications.
- [TASKS.md](TASKS.md) - Ordered implementation task checklist and acceptance criteria.
