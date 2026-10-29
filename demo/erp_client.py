#!/usr/bin/env python3
"""Sample ERP Integration Client for AICTE APAAR System.

SPEC.md Section 17 & TASKS.md T36:
- Authenticates with scoped API keys (X-API-Key or Authorization: Bearer).
- Pushes student data batches formatted as JSON.
- Uses Idempotency-Key header to prevent duplicate submissions.
- Evaluates records using the unified pure validation engine.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def make_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    """Helper to perform HTTP requests using Python standard library."""
    req_headers = {"User-Agent": "APAAR-ERP-Client/1.0", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    body_bytes = None
    if data is not None:
        body_bytes = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body_bytes, headers=req_headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_code = resp.status
            resp_body = resp.read().decode("utf-8")
            resp_headers = dict(resp.headers)
            parsed_body = json.loads(resp_body) if resp_body else {}
            return resp_code, parsed_body, resp_headers
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            parsed_error = json.loads(error_body)
        except Exception:
            parsed_error = {"detail": error_body}
        return e.code, parsed_error, dict(e.headers)
    except Exception as e:
        print(f"[ERROR] Network connection failed: {e}")
        sys.exit(1)


def acquire_demo_api_key(base_url: str, email: str, password: str) -> tuple[int, str]:
    """Obtain an integration API key using demo college admin credentials."""
    print(f"[*] Authenticating as college admin '{email}'...")
    login_url = f"{base_url}/api/v1/auth/login"
    status_code, body, _ = make_request(
        login_url,
        method="POST",
        data={"email": email, "password": password},
    )

    token = None
    if status_code == 200:
        token = body.get("access_token")
    elif status_code == 202:
        # MFA pending flow
        mfa_token = body.get("mfa_pending_token")
        verify_url = f"{base_url}/api/v1/auth/mfa/verify"
        s2, b2, _ = make_request(
            verify_url,
            method="POST",
            data={"mfa_pending_token": mfa_token, "code": "123456"},
        )
        if s2 == 200:
            token = b2.get("access_token")

    if not token:
        print(f"[FAIL] Could not obtain auth token for {email}: status={status_code}, detail={body}")
        sys.exit(1)

    print("[*] Successfully logged in. Inspecting user profile...")
    # Inspect user to find institution_id
    auth_header = {"Authorization": f"Bearer {token}"}
    s_user, b_user, _ = make_request(f"{base_url}/api/v1/auth/me", headers=auth_header)
    inst_id = b_user.get("institution_id")
    if not inst_id:
        print("[FAIL] Authenticated user is not associated with an institution.")
        sys.exit(1)

    print(f"[*] Institution ID: {inst_id}. Creating new ERP Integration API key...")
    create_key_url = f"{base_url}/api/v1/institutions/{inst_id}/api-keys"
    s_key, b_key, _ = make_request(
        create_key_url,
        method="POST",
        headers=auth_header,
        data={
            "name": f"Campus ERP Client {int(time.time())}",
            "scopes": ["students:write", "students:read", "courses:read"],
        },
    )

    if s_key != 201:
        print(f"[FAIL] Failed to generate API key: status={s_key}, detail={b_key}")
        sys.exit(1)

    raw_key = b_key["raw_key"]
    print(f"[+] API Key generated successfully: {b_key['key_prefix']} (key_id={b_key['id']})")
    return inst_id, raw_key


def generate_sample_student_batch(year: str = "2026-27") -> list[dict[str, Any]]:
    """Build a compliant demonstration batch of student records for ERP ingestion."""
    timestamp_suffix = int(time.time()) % 10000
    return [
        {
            "apaar_id": "900012345678",
            "name": "Rahul Sharma",
            "dob": "2004-05-15",
            "gender": "Male",
            "course": "Computer Science and Engineering",
            "branch": "Computer Science",
            "enrolment_no": f"ERP-{year[:4]}-{timestamp_suffix:04d}-01",
            "admission_date": "2026-07-15",
            "admission_mode": "State counselling",
            "seat_type": "Regular",
            "reservation_category": "General",
            "nri": "No",
            "oci": "No",
            "foreign_national": "No",
            "country": None,
        },
        {
            "apaar_id": "900012345679",
            "name": "Priya Patel",
            "dob": "2004-08-22",
            "gender": "Female",
            "course": "Computer Science and Engineering",
            "branch": "Computer Science",
            "enrolment_no": f"ERP-{year[:4]}-{timestamp_suffix:04d}-02",
            "admission_date": "2026-07-16",
            "admission_mode": "State counselling",
            "seat_type": "Regular",
            "reservation_category": "OBC",
            "nri": "No",
            "oci": "No",
            "foreign_national": "No",
            "country": None,
        },
        {
            "apaar_id": "900012345680",
            "name": "Vikram Singh",
            "dob": "2004-03-10",
            "gender": "Male",
            "course": "Mechanical Engineering",
            "branch": "Mechanical",
            "enrolment_no": f"ERP-{year[:4]}-{timestamp_suffix:04d}-03",
            "admission_date": "2026-07-18",
            "admission_mode": "JEE Main",
            "seat_type": "Supernumerary",
            "reservation_category": "General",
            "nri": "No",
            "oci": "No",
            "foreign_national": "No",
            "country": None,
        },
    ]


def run_erp_demo(
    base_url: str,
    api_key: str | None = None,
    email: str = "admin@ngec-nagpur.gov.in",
    password: str = "Demo@12345",
    academic_year: str = "2026-27",
) -> None:
    """Execute end-to-end ERP synchronization demonstration."""
    print("=" * 70)
    print("AICTE APAAR - External ERP Integration Client (SPEC 17 / T36)")
    print("=" * 70)

    # 1. Acquire API key if not supplied
    if not api_key:
        _, api_key = acquire_demo_api_key(base_url, email, password)

    # 2. Inspect API key identity
    print("\n[*] Step 1: Checking API Key Identity (/api/v1/integration/me)...")
    me_url = f"{base_url}/api/v1/integration/me"
    status_code, me_data, _ = make_request(me_url, headers={"X-API-Key": api_key})
    if status_code != 200:
        print(f"[FAIL] /api/v1/integration/me failed with status {status_code}: {me_data}")
        sys.exit(1)

    print(f"[+] Authenticated as Institution: {me_data['institution_name']} (AICTE ID: {me_data['aicte_id']})")
    print(f"[+] Key Name: '{me_data['api_key_name']}', Scopes: {me_data['scopes']}")

    # 3. Prepare Batch
    students_batch = generate_sample_student_batch(academic_year)
    idempotency_key = f"DEMO-ERP-BATCH-{int(time.time())}"

    print(f"\n[*] Step 2: Pushing batch of {len(students_batch)} student records...")
    print(f"[*] Idempotency Key: {idempotency_key}")

    push_url = f"{base_url}/api/v1/integration/students/bulk"
    payload = {
        "academic_year": academic_year,
        "students": students_batch,
    }

    push_headers = {
        "X-API-Key": api_key,
        "Idempotency-Key": idempotency_key,
    }

    # First Attempt
    t0 = time.time()
    s_push, b_push, h_push = make_request(
        push_url,
        method="POST",
        headers=push_headers,
        data=payload,
    )
    elapsed = (time.time() - t0) * 1000

    if s_push not in (200, 201):
        print(f"[FAIL] Student push failed: HTTP {s_push}: {b_push}")
        sys.exit(1)

    summary = b_push.get("summary", {})
    replayed = h_push.get("x-idempotent-replayed", "false")

    print(f"[+] Batch Ingested in {elapsed:.1f}ms - HTTP {s_push}")
    print(f"[+] Upload ID:        {b_push.get('upload_id')}")
    print(f"[+] Total Records:    {summary.get('total_rows')}")
    print(f"[+] Valid Records:    {summary.get('valid_rows')}")
    print(f"[+] Flagged Records:  {summary.get('flagged_rows')}")
    print(f"[+] Errors Count:     {summary.get('error_count')}")
    print(f"[+] Warnings Count:   {summary.get('warning_count')}")
    print(f"[+] Replay Header:    X-Idempotent-Replayed = {replayed}")

    # 4. Demonstrate Idempotency Replay
    print("\n[*] Step 3: Verifying Idempotency Replay (submitting identical request)...")
    s_replay, b_replay, h_replay = make_request(
        push_url,
        method="POST",
        headers=push_headers,
        data=payload,
    )

    is_replayed = h_replay.get("x-idempotent-replayed", "").lower() == "true"
    same_upload_id = b_replay.get("upload_id") == b_push.get("upload_id")

    if s_replay in (200, 201) and is_replayed and same_upload_id:
        print("[+] SUCCESS: Idempotency confirmed! Server returned cached response.")
        print(f"[+] HTTP Status:      {s_replay}")
        print(f"[+] Replay Header:    X-Idempotent-Replayed = {h_replay.get('x-idempotent-replayed')}")
        print(f"[+] Upload ID Match:  {b_replay.get('upload_id')} == {b_push.get('upload_id')}")
    else:
        print(f"[WARN] Idempotency mismatch: status={s_replay}, replayed={is_replayed}, headers={h_replay}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE: External ERP batch successfully pushed and validated.")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Sample ERP Client for AICTE APAAR Integration")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base API URL")
    parser.add_argument("--key", default=None, help="Pre-generated API key")
    parser.add_argument("--email", default="admin@ngec-nagpur.gov.in", help="College admin email")
    parser.add_argument("--password", default="Demo@12345", help="College admin password")
    parser.add_argument("--year", default="2026-27", help="Academic year")
    args = parser.parse_args()

    run_erp_demo(
        base_url=args.url.rstrip("/"),
        api_key=args.key,
        email=args.email,
        password=args.password,
        academic_year=args.year,
    )


if __name__ == "__main__":
    main()
