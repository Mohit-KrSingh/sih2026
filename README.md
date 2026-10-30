# EduTrace: Student Data Management and Verification System

A student team project for the Smart India Hackathon AICTE problem statement: managing and verifying student records keyed by the 12-digit APAAR ID.

> **Demo mode notice**: APAAR registry is simulated. EduTrace is a prototype and not an official government service. External dependencies (APAAR registry, AICTE master list, OTP delivery, identity verification, and file storage) are simulated with clean interface mocks and HTTP client stubs for local evaluation. No official government emblem or seals are used.

---

## What it is

Today, most technical institutions submit aggregate enrolment figures to regulatory bodies rather than student-level data. Because of this, regulators cannot detect admissions beyond approved intake capacity or identify students enrolled concurrently at multiple colleges.

EduTrace provides a unified platform and API for colleges to upload student records linked to their 12-digit APAAR ID. Every submission runs through an automated validation engine that checks format, age criteria, approved course quotas, and cross-institutional duplicates. Regulatory officers monitor admissions in real time through live dashboards, while authorized third parties can verify credentials with student consent under India's Digital Personal Data Protection (DPDP) principles.

An **APAAR ID** (Automated Permanent Academic Account Registry) is a unique 12-digit lifelong academic identifier assigned to students in India.

### Core features

- **Institution data entry**: Single student forms, bulk CSV upload, and a REST API for campus ERP systems.
- **Validation engine**: 34 pure validation rules running cheap checks first (file structure, APAAR registry lookups, course limits, duplicates, and statistical anomalies).
- **Compliance review queue**: Institutions can attach official justifications for compliance exceptions; regulatory officers review and accept, query, or escalate.
- **Real-time monitoring**: Live dashboard feeds over Server-Sent Events showing over-intake institutions, duplicate enrolments, and quota utilization.
- **Consented verification**: Students approve verification requests in their portal; verifiers receive minimal academic records with Ed25519 digital signatures and tamper-evident QR codes.

---

## UX4G Design System & Accessibility

EduTrace's user interface is built on **UX4G Design System 3.0** (`ux4g-web-components`), the official Government of India design system by NeGD / MeitY.

Key design system implementation details:
- **Design tokens**: All visual styles use official UX4G semantic tokens (`--ux4g-*`) for colour, typography, spacing, and elevation. Tailwind CSS is restricted to structural layout utilities.
- **Typography**: Uses bundled **Noto Sans** (Latin and Devanagari subsets) with system font fallbacks, ensuring reliable offline functionality.
- **Reusable component layer**: Built with modular UX4G component wrappers (`Button`, `Card`, `Badge`, `Alert`, `Table`, `Input`, `Select`, `Stepper`, `Pagination`).
- **Accessibility (WCAG 2.1 AA)**: Keyboard-operable across every route, visible focus ring on all interactive elements, skip link landing on the main landmark, and an accessibility toolkit for text resizing, high contrast, theme toggle, and reduced motion.
- **Standardized badges & alerts**: Uniform visual severity hierarchy across error (red filled), exception (red outline), warning (amber), and info (neutral).

Detailed audit results and checklist are documented in [docs/UX4G_COMPLIANCE.md](docs/UX4G_COMPLIANCE.md).

---

## User Interface Screenshots

Clean application screenshots captured at 1280x800 desktop resolution under `docs/screens/`:

| Screen | Description | File |
|---|---|---|
| **Public Landing Page** | Hero, APAAR explainer, entry cards for all roles, and workflow steps. | [docs/screens/home.png](docs/screens/home.png) |
| **Institution Activation** | Four-step stepper for claiming college accounts via on-file official contacts. | [docs/screens/activate.png](docs/screens/activate.png) |
| **Bulk CSV Upload Result** | Upload summary card, pass/flag counters, and row-level validation table. | [docs/screens/upload-result.png](docs/screens/upload-result.png) |
| **Validation & Flags** | Filterable compliance flags with inline justifications and document references. | [docs/screens/validation-flags.png](docs/screens/validation-flags.png) |
| **College Dashboard** | Approved intake quotas, regular admitted counts, and capacity alert badges. | [docs/screens/college-dashboard.png](docs/screens/college-dashboard.png) |
| **AICTE National Overview** | Metric cards, submission progress, red list of over-intake colleges, and live feed. | [docs/screens/aicte-overview.png](docs/screens/aicte-overview.png) |
| **Intake Compliance** | National compliance table tracking intake capacity against actual enrolments. | [docs/screens/compliance.png](docs/screens/compliance.png) |
| **Intelligent Anomalies** | Anomaly detection alerts with explanations and ML IsolationForest scatter plot. | [docs/screens/anomalies.png](docs/screens/anomalies.png) |
| **Consented Verification** | Cryptographic verification card with zero personal data leakage banner. | [docs/screens/verify-consent.png](docs/screens/verify-consent.png) |
| **Verifiable Degree Certificate** | Sample certificate with side-by-side College Student ID, APAAR ID, and QR code. | [docs/screens/certificate.png](docs/screens/certificate.png) |

---

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite, UX4G Design System 3.0 (`ux4g-web-components`), Noto Sans, Material Symbols, ECharts.
- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (sync), Alembic.
- **Database & Cache**: PostgreSQL 16, Redis 7 (OTP expiry, sliding-window rate limits, SSE pub/sub).
- **Validation & ML**: pandas, RapidFuzz, scikit-learn (IsolationForest).
- **Cryptography & Documents**: PyNaCl (Ed25519 signing), argon2-cffi, PyJWT, Fernet (encrypted DOB), ReportLab (PDF), openpyxl (XLSX), qrcode.

---

## How to run it

You can run the full platform using Docker Compose or directly on your machine.

### Option A: With Docker Compose

```bash
# Clone the repository
git clone <repo-url>
cd sih2026

# Copy environment variables
cp .env.example .env

# Start all services (Postgres, Redis, Backend, Frontend)
make up
# or: docker compose up -d

# Seed demo institutions, quotas, and test students
make seed

# Check system health
curl http://localhost:8000/api/v1/health

# Stop everything when done
make down
```

### Option B: Local Setup (without Docker)

Prerequisites: Python 3.12, Node.js 20+, PostgreSQL 16, and Redis 7.

```powershell
# 1. Setup Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# 2. Setup frontend dependencies
cd frontend
npm install
cd ..

# 3. Start databases and services
make up

# 4. Run database migrations
alembic -c backend/alembic.ini upgrade head

# 5. Seed demo data
make seed
```

### URLs

- Web Portal: [http://localhost:5173](http://localhost:5173)
- Backend API: [http://localhost:8000](http://localhost:8000)
- API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- Student Consent Portal: [http://localhost:5173/student](http://localhost:5173/student)
- Public Verification: [http://localhost:5173/verify](http://localhost:5173/verify)

---

## Standard Commands

We provide shortcuts in the Makefile (and matching scripts in `scripts/`):

| Command | What it does |
|---|---|
| `make up` | Starts PostgreSQL 16, Redis 7, backend API, and frontend dev server. |
| `make down` | Stops all running services. |
| `make test` | Runs the test suite (backend pytest + frontend vitest + Playwright e2e/a11y). |
| `make lint` | Runs code quality checks (ruff on backend, eslint on frontend, token check, microcopy check). |
| `make seed` | Seeds 30 demo colleges, courses, quotas, and test students. |
| `make demo` | Resets the database to a clean scripted demo state. |
| `make rules-doc` | Regenerates `docs/RULES.md` from the Python validation rule registry. |
| `make brand-check` | Verifies that all brand naming rules are preserved across the codebase. |

---

## Demo Accounts

All demo accounts use password **`Demo@12345`**.

| Role | Email / Identifier | College / Organization | What you can test |
|---|---|---|---|
| **`aicte_admin`** | `aicte_admin@aicte-india.org` | AICTE Headquarters | Rule configuration tuning, audit log verification, verifier approvals. |
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

As required by system architecture rules, every external dependency sits behind a clean Python Protocol interface. For local execution and evaluations, mock classes serve test data. Production client classes exist as stubs and raise `NotImplementedError` until live government credentials and endpoints are configured.

| Dependency | Interface | Mock class | Real class stub | Setting & Default | Notes |
|---|---|---|---|---|---|
| APAAR Registry | `ApaarClient` | `MockApaarClient` | `HttpApaarClient` | `APAAR_CLIENT_TYPE="mock"` | Checks `mock_apaar_registry` table with RapidFuzz name matching. |
| AICTE Master Directory | `AicteMasterClient` | `MockAicteMasterClient` | `HttpAicteMasterClient` | `AICTE_MASTER_CLIENT_TYPE="mock"` | Provides 30 demo colleges across 8 states with approved intakes. |
| OTP / SMS Service | `OtpSender` | `MockOtpSender` | `HttpOtpSender` | `OTP_SENDER_TYPE="mock"` | Saves OTPs to Redis (5 min TTL) and logs them to `dev_outbox`. |
| Signatory Check | `IdentityVerifier` | `MockIdentityVerifier` | `HttpIdentityVerifier` | `IDENTITY_VERIFIER_TYPE="mock"` | Simulates head-of-institution signatory verification during activation. |
| Evidence Storage | `Storage` | `LocalStorage` | `HttpStorage` | `STORAGE_TYPE="mock"` | Stores uploaded justifications and evidence on disk under `uploads/`. |

---

## Known Limitations

We built this prototype for the hackathon evaluation, with the following practical constraints:
1. **Simulated external registries**: We do not connect to production APAAR or DigiLocker endpoints because live credentials require statutory accreditation. All registry queries use seeded test records.
2. **Single-server event stream**: The SSE activity feed uses an in-process Redis pub/sub listener. It serves local evaluations well but would require a distributed message broker for national-scale concurrent traffic.
3. **Synthetic anomaly baseline**: The IsolationForest anomaly detection model is fitted on historical demo distributions. In a nationwide deployment, regulators would train it across multi-year admission histories.
4. **Local file uploads**: Justification PDFs and evidence files are saved on the local filesystem rather than cloud object storage.
5. **No Aadhaar storage**: In strict compliance with DPDP principles and system rules, we never collect or store Aadhaar numbers.

---

## Documentation Links

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture, sequence diagrams, and validation pipeline.
- [docs/RULES.md](docs/RULES.md) - Complete validation rules catalogue and severity levels.
- [docs/UX4G_COMPLIANCE.md](docs/UX4G_COMPLIANCE.md) - UX4G design system compliance report, foundations audit, and test evidence.
- [demo/DEMO.md](demo/DEMO.md) - Step-by-step evaluator click guide for all demo scenarios.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Team & Credits

Built for Smart India Hackathon 2026.
Special thanks to AICTE and the Ministry of Education for the problem statement.
