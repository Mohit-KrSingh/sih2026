# APAAR Platform - Scripted Demonstration Guide

This guide walks evaluators and Smart India Hackathon judges through the complete capabilities of the **APAAR Student Data Management and Verification System**.

Every scenario in this document can be reproduced from scratch using the one-command reset:
```bash
make demo
```
*(Windows PowerShell equivalent: `powershell -ExecutionPolicy Bypass -File scripts/demo.ps1`)*

---

## 1. Environment & Demo Accounts

### 1.1 Quick Start
1. **Reset Database to Demo State**:
   ```bash
   make demo
   ```
2. **Start the Platform Stack**:
   ```bash
   make up
   ```
3. **Open the Web Application**:
   - **Frontend UI**: [http://localhost:5173](http://localhost:5173)
   - **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Endpoint**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

> [!NOTE]
> In accordance with Hard Rule 10, all simulated identity lookups and mock third-party services are explicitly declared in the application footer: **"Demo mode: APAAR registry is simulated"**.

### 1.2 Pre-Configured Demo Credentials
All demo accounts use password: `Demo@12345`  
*(MFA TOTP code for regulatory & admin logins: `123456` or mock authenticator)*

| Stakeholder Role | Email / Identifier | Purpose / Pre-Seeded State |
|---|---|---|
| **AICTE Administrator** | `aicte_admin@aicte-india.org` | National oversight, rule configuration overrides, verifier approvals, audit chain verification. |
| **AICTE Regulatory Officer** | `aicte_officer@aicte-india.org` | Live compliance monitoring, over-intake red list, anomaly detection, review queue decisions. |
| **College Admin (Clean)** | `admin@piaet-pune.edu.in` | Pune Institute of Advanced Engineering & Technology (`1-10000001`). Submitted cleanly, receipt issued. |
| **College Admin (Exceptions)** | `admin@mmit-mumbai.ac.in` | Mumbai Metropolitan Institute of Technology (`1-10000002`). Submitted with over-intake exception & duplicate student. |
| **College Admin (Draft)** | `admin@ngec-nagpur.gov.in` | Nagpur Government Engineering College (`1-10000003`). In draft stage for live CSV upload demonstrations. |
| **Authorized Verifier** | `verifier@tcs-verifications.com` | Tata Consultancy Services Background Verifications. Registered & approved employer verifier. |
| **Demo Student** | APAAR ID: `111122223333` | Aarav Sharma (Clean 2025-26 history, active verifiable credential `VR-2025-111122223333`). |
| **Duplicate Student** | APAAR ID: `555566667777` | Priya Patel (Planted dual-enrolment across Pune Institute and Mumbai Metropolitan). |

---

## 2. Walkthrough Scenarios

### Scenario 1: Over-Intake Flagged Red (Intake Exceeded & Visual Hierarchy)
*Demonstrates: Problem Statement Requirement 3, Hard Rule 1 & SPEC.md Section 9.3, 12, 13.*

#### Step 1: Institutional Perspective (MMIT Mumbai)
1. Navigate to [http://localhost:5173/login/college](http://localhost:5173/login/college).
2. Log in as:
   - **Email**: `admin@mmit-mumbai.ac.in`
   - **Password**: `Demo@12345`
3. Land on `/college/dashboard`.
4. Observe the **Course Summary Table**:
   - **B.Tech in Data Science & Business Analytics**:
     - **Approved Intake**: `60` with a padlock icon (locked AICTE quota; colleges cannot alter this per Hard Rule 1).
     - **Regular Admitted**: `68`
     - **Status Badge**: Bold Red Pill labeled **"Over limit by 8"**.
5. Navigate to `/college/seats`:
   - Inspect the declared seats breakdown showing 68 admitted students against 60 approved capacity.
6. Navigate to `/college/validation`:
   - Inspect the exception card for rule `INTAKE_EXCEEDED`:
     - **Level**: Red outlined `Exception` badge.
     - **Message**: *"Regular admitted count (68) exceeds approved intake (60) by 8 students."*
     - **Justification**: College has attached court order `court_order_wp2026_89.pdf` explaining the 8 excess seats.

#### Step 2: AICTE Central Regulator Perspective
1. Log out or open an incognito window at [http://localhost:5173/login/aicte](http://localhost:5173/login/aicte).
2. Log in as:
   - **Email**: `aicte_officer@aicte-india.org`
   - **Password**: `Demo@12345`
   - **MFA Code**: `123456`
3. Navigate to `/aicte/overview`:
   - Notice the prominent **Red List of Over-Intake Institutions**:
     - **Mumbai Metropolitan Institute of Technology** (`1-10000002`) appears at the top highlighted in high-contrast red alert styling.
4. Click on the institution or navigate to `/aicte/intake`:
   - Filter by State `Maharashtra`.
   - Drill down into Data Science & Business Analytics to see exact capacity overshoot (68 / 60, +13.3%).

#### Step 3: Live Upload Trigger Test
1. Log in as College 3: `admin@ngec-nagpur.gov.in` / `Demo@12345`.
2. Navigate to `/college/upload`.
3. Choose Course **Mechanical Engineering** (approved intake: 60).
4. Upload `demo/overintake_upload.csv` (contains 70 valid rows).
5. **Expected Result**: The validation engine calculates regular admitted + pending rows (70 > 60), halts submission, and immediately flags `INTAKE_EXCEEDED` in red.

---

### Scenario 2: Cross-College Duplicate Caught (Dual Enrolment Prevention)
*Demonstrates: Problem Statement Requirement 3, Hard Rule 4 & SPEC.md Section 9.3, 10, 12.*

#### Step 1: AICTE Duplicate Case Investigation
1. Log in as `aicte_officer@aicte-india.org` at [http://localhost:5173/login/aicte](http://localhost:5173/login/aicte).
2. In the top navigation, click **Duplicates** (`/aicte/duplicates`).
3. Locate the flagged duplicate enrolment case for **Priya Patel** (APAAR ID: `555566667777`):
   - Notice the side-by-side institutional enrolment cards:
     - **Institution A**: Pune Institute of Advanced Engineering & Technology (`1-10000001`) — *B.Tech Computer Science and Engineering* (Enrolment No: `EN26-PUNE-CSE-DUPE`).
     - **Institution B**: Mumbai Metropolitan Institute of Technology (`1-10000002`) — *B.Tech Information Technology* (Enrolment No: `EN26-MMIT-IT-DUPE`).
   - Rule code: `DUP_ACTIVE_OTHER_COLLEGE`.
   - Level: `Warning` / `Exception` flagged simultaneously across both submissions.

#### Step 2: College Notifications
1. Log in as Pune Admin: `admin@piaet-pune.edu.in` / `Demo@12345`.
2. On `/college/dashboard`, check the **Notifications Panel**:
   - Alert: *"APAAR ID 555566667777 is active at Mumbai Metropolitan Institute of Technology for academic year 2026-27."*
3. Both colleges are alerted to resolve student seat allocation before final approval.

#### Step 3: Live Upload Catch
1. Log in as Nagpur Admin: `admin@ngec-nagpur.gov.in` / `Demo@12345`.
2. Go to `/college/upload`.
3. Upload `demo/cross_college_dupe.csv`.
4. **Expected Result**: The batch upload validator queries the central index on `(apaar_id, academic_year)` and catches the conflict in real time, preventing undetected double-admissions.

---

### Scenario 3: Intelligent Anomaly Alerts with Human-Readable Explanations
*Demonstrates: Problem Statement Requirement 3, SPEC.md Section 9.3, 12.*

1. Log in as `aicte_officer@aicte-india.org` at [http://localhost:5173/login/aicte](http://localhost:5173/login/aicte).
2. In the navigation, click **Anomalies** (`/aicte/anomalies`).
3. Walk through the three planted anomaly categories:

| Anomaly Type | Flagged Institution & Course | Detected Metric & Explanation | Regulatory Hint / Action |
|---|---|---|---|
| **Sudden Enrolment Jump** | **Bharat National Institute of Tech** (`1-10000004`)<br>B.Tech Computer Science | **Enrolment jumped +100.0%** (80 in 2025-26 to 160 in 2026-27). Exceeds statutory 30% jump limit. | *"Verify admission register and council approval for intake scaling."* |
| **Date of Birth Cluster** | **Mysuru Royal College of Engg** (`1-10000005`)<br>B.Tech Mechanical Engineering | **8 students share exact DOB `2005-08-15`** (threshold: 5 students). Indicates synthetic record batching. | *"Verify identity documentation for date of birth records."* |
| **Sequential APAAR Run** | **Hubballi Technological Inst** (`1-10000006`)<br>B.Tech Computer Engineering | **12 consecutive APAAR IDs** (`990000000101` to `990000000112`). | *"Audit registration logs to rule out bulk automated synthetic identity submission."* |
| **Statistical Outliers** | Machine Learning IsolationForest | Unsupervised anomaly score computed across 6 normalized features. | Visualized in the Anomaly Scatter Plot. |

---

### Scenario 4: Live Dashboard Update (Real-Time SSE Monitoring)
*Demonstrates: Problem Statement Requirement 4, SPEC.md Section 3, 12, 18.*

1. Arrange two browser windows side-by-side:
   - **Window A (Regulator)**: Logged in as `aicte_officer@aicte-india.org` on [http://localhost:5173/aicte/overview](http://localhost:5173/aicte/overview).
   - **Window B (Institution)**: Open terminal or second browser tab.
2. In Window B terminal, execute an automated batch ingestion via the ERP client:
   ```bash
   python demo/erp_client.py
   ```
   *(Or alternatively, log in as `admin@ngec-nagpur.gov.in` and upload `demo/clean_upload.csv`)*.
3. Observe **Window A**:
   - Without refreshing the page, the **Live Activity Feed** receives the real-time event dispatched via Server-Sent Events (SSE).
   - The submission counters and intake utilization graphs update live.
   - The green pulsing indicator confirms active real-time connection to `/api/v1/analytics/stream`.

---

### Scenario 5: Consent-Based Verification (DPDP Compliance & Minimal Disclosure)
*Demonstrates: Problem Statement Requirement 5, 6, 8 & SPEC.md Section 14, 16.*

#### Step 1: Employer Consent Request
1. Open [http://localhost:5173/verify](http://localhost:5173/verify) and click **Verifier Login** (or go to `/login/aicte`).
2. Log in as:
   - **Email**: `verifier@tcs-verifications.com`
   - **Password**: `Demo@12345`
3. Navigate to `/verifier/search`.
4. Search for student:
   - **APAAR ID**: `111122223333` (Aarav Sharma)
   - **Verification Purpose**: `Employment background verification for Associate Software Engineer`
5. Click **Request Student Consent**.
6. System displays: *"Consent request sent to student. Awaiting digital authorisation."*

#### Step 2: Student Consent Portal
1. Open an incognito browser window and navigate to [http://localhost:5173/student](http://localhost:5173/student).
2. Enter APAAR ID: `111122223333`.
3. Click **Send OTP**.
4. In the mock demo environment, click **Autofill Demo OTP** (or read the generated OTP from `/api/v1/dev/outbox`).
5. Click **Verify & Enter Portal**.
6. Under **Pending Verification Requests**:
   - Inspect the request from **Tata Consultancy Services - Background Verifications**.
   - Notice the DPDP Data Minimisation disclosure:
     - **Disclosed Fields**: Institution Name, Course, Academic Year, Status.
     - **Excluded / Protected Fields**: Date of Birth, Reservation Category, Religion, Address, Phone Number.
7. Click **Approve Consent**.

#### Step 3: Minimal Record Disclosure
1. Return to the Verifier tab and navigate to `/verifier/history` (or re-search `111122223333`).
2. The student card is now unlocked and displays:
   - **Student Name**: Aarav Sharma
   - **Institution**: Pune Institute of Advanced Engineering & Technology
   - **Course**: Computer Science and Engineering
   - **Academic Year**: 2025-26
   - **Verification ID**: `VR-2025-111122223333`
   - **Status**: *"Verified by AICTE Central Repository"*
3. **DPDP Verification**: Confirm that Date of Birth, Category, and Contact data are completely absent, fulfilling India DPDP compliance.

---

### Scenario 6: QR Code & Cryptographic Tamper Check Failing
*Demonstrates: Problem Statement Requirement 6, 10 & SPEC.md Section 14, 17.*

#### Part A: Valid Credential Verification
1. Navigate to the public verification portal: [http://localhost:5173/verify](http://localhost:5173/verify).
2. In the Verification ID search field, enter:
   ```
   VR-2025-111122223333
   ```
3. Click **Verify Credential**.
4. **Expected Result**:
   - **Shield Icon**: Green Shield with checkmark.
   - **Status**: **"Cryptographically Verified by AICTE"**.
   - **Details**: Shows institution, course, year, and verification timestamp.
   - **Signature Verification**: Canonical Ed25519 signature verified against AICTE root public key.

#### Part B: Tamper Check Failing (Tampered Record Detected)
1. In the same search box on [http://localhost:5173/verify](http://localhost:5173/verify), enter the pre-seeded tampered credential:
   ```
   VR-TAMPERED-DEMO
   ```
   *(Or navigate directly to: [http://localhost:5173/verify?vid=VR-TAMPERED-DEMO](http://localhost:5173/verify?vid=VR-TAMPERED-DEMO))*.
2. **Expected Result**:
   - **Shield Icon**: Red Shield Alert icon.
   - **Alert Header**: **"SECURITY ALERT: SIGNATURE MISMATCH"**.
   - **Status**: **"Tampered Record Detected"**.
   - **Explanation**: *"The cryptographic Ed25519 signature does NOT match the academic record on file. One or more signed fields have been modified after issuance."*
   - **Security Warning**: *"This credential cannot be verified. Do not accept this document as proof of enrolment."*

#### Part C: Degree Certificate PDF with Side-by-Side IDs
1. Log in as Pune Admin (`admin@piaet-pune.edu.in`) or AICTE Officer (`aicte_officer@aicte-india.org`).
2. Navigate to `/college/students` or `/aicte/explore`.
3. Open the record for Aarav Sharma (`111122223333`) and click **Download Degree Certificate (PDF)**.
4. Open the generated PDF:
   - Notice **College Student ID** (`EN25-001-0001`) and **12-digit APAAR ID** (`1111 2222 3333`) printed prominently **side-by-side**.
   - Notice the verifiable QR code embedded on the certificate.
   - Scanning the QR code points to `/verify?vid=VR-2025-111122223333`, which executes the cryptographic verification flow without leaking PII.

---

### Scenario 7: Messy CSV Upload & Row-Level Validation Engine
*Demonstrates: Problem Statement Requirement 1, 2, 3 & SPEC.md Section 9.3.*

1. Log in as Nagpur College Admin: `admin@ngec-nagpur.gov.in` / `Demo@12345`.
2. Navigate to `/college/upload`.
3. Select Course: **Civil Engineering**.
4. Upload `demo/messy_upload.csv`.
5. **Expected Result**:
   - The validation engine executes all 17 row-level rules in one pass without saving unvalidated data.
   - Visual breakdown displays:
     - Missing APAAR IDs (`APAAR_REQUIRED`)
     - Malformed names with numbers (`NAME_FORMAT`)
     - Invalid future dates of birth (`DOB_INVALID`)
     - Unapproved courses (`COURSE_NOT_APPROVED`)
     - Age outside permitted UG bounds (`AGE_OUT_OF_RANGE`)
     - NRI/foreign nationality category conflicts (`CATEGORY_CONFLICT`)
   - Evaluator can click **Inline Edit** to resolve a row error and watch the validation badge transition from red `Error` to green `Passed`.

---

## 3. Automated Test Suite Reference
To independently verify that all demo scenarios pass automated test coverage:
```bash
# Run complete test suite (448 pytest tests + 108 vitest tests)
make test

# Run code style & linting checks
make lint

# Run End-to-End Playwright golden path suite
cd frontend && npx playwright test
```
