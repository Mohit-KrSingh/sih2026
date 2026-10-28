import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import path from "path";

test.describe("T34: Verification Portal and Student Consent End-to-End Golden Path", () => {
  const verifierEmail = "verifier@tcs-verifications.com";
  const verifierPassword = "Demo@12345";
  const studentApaarId = "111122223333";
  const purposeText = "Senior Cloud Architect pre-employment background verification";

  test.beforeEach(async () => {
    try {
      const rootDir = path.resolve(process.cwd(), "..");
      const resetCmd = `"${path.join(rootDir, ".venv/Scripts/python.exe")}" -c "import sys; sys.path.insert(0, 'backend'); from app.db import get_redis; r = next(get_redis()); keys = r.keys('ratelimit:*'); (r.delete(*keys) if keys else None)"`;
      execSync(resetCmd, { cwd: rootDir });
    } catch (e) {
      console.warn("Rate limit reset warning:", e);
    }
  });

  test("completes end-to-end verification with student consent lifecycle", async ({
    page,
    request,
  }) => {
    // -------------------------------------------------------------------------
    // Step 1: Verifier signs in and navigates to Verifier Portal
    // -------------------------------------------------------------------------
    await page.goto("/login/college");
    await expect(page.locator("h1")).toContainText("College Portal Login");

    // Click demo quick-fill for Verifier Portal
    const verifierBtn = page.getByText("Tata Consultancy Services (Verifier)");
    await expect(verifierBtn).toBeVisible({ timeout: 10000 });
    await verifierBtn.click();

    // Submit login form
    const signInBtn = page.getByRole("button", { name: "Sign in as college" });
    await signInBtn.click();

    // Verify redirection to Verifier Search screen
    await page.waitForURL("**/verifier/search**", { timeout: 10000 });
    await expect(page.locator("h1")).toContainText("Stakeholder Credential Verification");
    await expect(
      page.getByText("Tata Consultancy Services - Background Verifications")
    ).toBeVisible({ timeout: 10000 });

    // -------------------------------------------------------------------------
    // Step 2: Verifier initiates consent request for demo student
    // -------------------------------------------------------------------------
    const apaarInput = page.getByLabel("Student 12-Digit APAAR ID");
    await apaarInput.fill(studentApaarId);

    const purposeInput = page.getByLabel("Verification Purpose (DPDP Compliance)");
    await purposeInput.fill(purposeText);

    const requestBtn = page.getByRole("button", { name: "Request student consent" });
    await requestBtn.click();

    // Confirm active consent card appears with pending status and 24-hour statutory TTL
    await expect(page.getByText("Consent Request #")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("24-Hour Expiry Window")).toBeVisible();
    await expect(page.getByText(/Awaiting Student Authorization/i)).toBeVisible();

    // Extract request ID from text
    const reqText = await page.getByText(/Consent Request #\d+/).textContent();
    const reqIdMatch = reqText?.match(/\d+/);
    const requestId = reqIdMatch ? reqIdMatch[0] : "";
    expect(requestId).not.toBe("");

    // -------------------------------------------------------------------------
    // Step 3: Student authenticates into Student Consent Portal (/student)
    // -------------------------------------------------------------------------
    // Clear storage for fresh student session
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    await page.goto("/student");
    await expect(page.locator("h1")).toContainText("Student Consent & Record Portal");

    // Fill student APAAR ID
    const studentInput = page.getByLabel("APAAR Identification Number");
    await studentInput.fill(studentApaarId);

    const sendOtpBtn = page.getByRole("button", { name: "Send verification OTP" });
    await sendOtpBtn.click();

    // Confirm step 2 OTP form appears
    await expect(page.getByText("Step 2: Enter Verification OTP")).toBeVisible({
      timeout: 10000,
    });

    // Fetch the dispatched OTP from dev outbox
    await page.waitForTimeout(1000);
    const outboxResp = await request.get(
      `http://127.0.0.1:8000/api/v1/dev/outbox?recipient=${studentApaarId}`
    );
    expect(outboxResp.ok()).toBeTruthy();
    const outboxData = await outboxResp.json();
    expect(outboxData.length).toBeGreaterThan(0);

    const latestMsg = outboxData[0].body;
    const otpMatch = latestMsg.match(/\b\d{6}\b/);
    expect(otpMatch).not.toBeNull();
    const otpCode = otpMatch ? otpMatch[0] : "";
    expect(otpCode).toHaveLength(6);

    // Enter OTP
    const otpInput = page.getByLabel("6-Digit OTP");
    await otpInput.fill(otpCode);

    const accessBtn = page.getByRole("button", { name: "Access records" });
    await accessBtn.click();

    // -------------------------------------------------------------------------
    // Step 4: Student views academic records & approves the pending consent request
    // -------------------------------------------------------------------------
    await expect(page.getByText("Aarav Sharma")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Verified in Central Registry")).toBeVisible();

    // Verify institutional enrolment record is listed
    await expect(
      page.getByText("Pune Institute of Advanced Engineering & Technology")
    ).toBeVisible({ timeout: 10000 });

    // Verify pending request from TCS is displayed
    await expect(
      page.getByText("Tata Consultancy Services - Background Verifications").first()
    ).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(purposeText).first()).toBeVisible();

    // Student approves consent
    const approveBtn = page.getByRole("button", { name: "Approve consent" });
    await expect(approveBtn.first()).toBeVisible();
    await approveBtn.first().click();

    // Verify confirmation notice appears
    await expect(page.getByText(/Consent approved/i)).toBeVisible({ timeout: 10000 });

    // -------------------------------------------------------------------------
    // Step 5: Verifier accesses consented student record with minimal fields
    // -------------------------------------------------------------------------
    // Sign back in as verifier
    await page.goto("/login/college");
    await page.getByLabel("Official Institutional Email").fill(verifierEmail);
    await page.getByLabel("Password").fill(verifierPassword);
    await page.getByRole("button", { name: "Sign in as college" }).click();

    await page.waitForURL("**/verifier/search**", { timeout: 10000 });

    // Navigate to Verifier History to view all requests
    await page.goto("/verifier/history");
    await expect(page.locator("h1")).toContainText("Verification & Consent History");

    // Verify the approved request is in the table
    await expect(page.getByText(purposeText).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Approved").first()).toBeVisible();

    // Click "View record"
    const viewRecordBtn = page.getByRole("button", { name: "View record" });
    await expect(viewRecordBtn.first()).toBeVisible();
    await viewRecordBtn.first().click();

    // Verify Consented Academic Verification Modal opens
    await expect(page.getByText("Consented Academic Verification")).toBeVisible({
      timeout: 10000,
    });
    await expect(
      page.getByText("Pune Institute of Advanced Engineering & Technology")
    ).toBeVisible();

    // DPDP Zero PII Verification:
    await expect(page.getByText(/Zero PII Guaranteed/i)).toBeVisible();

    // Close modal
    await page.getByRole("button", { name: "Close" }).click();

    // -------------------------------------------------------------------------
    // Step 6: Public verification portal (/verify) checks
    // -------------------------------------------------------------------------
    // 6a: Direct lookup with valid VID QR link
    await page.goto("/verify?vid=VR-2025-111122223333");
    await expect(page.locator("h1")).toContainText("Verify Student Academic Credential");
    await expect(
      page.getByText("Cryptographically Valid Credential")
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText("Ed25519 Digital Signature Verified")
    ).toBeVisible();
    await expect(
      page.getByText("Zero Personal Data Leak", { exact: false })
    ).toBeVisible();

    // 6b: Enter 12-digit APAAR ID -> triggers DPDP consent requirement notice
    const queryInput = page.getByLabel("Verification Identifier (VID) or APAAR ID");
    await queryInput.fill(studentApaarId);

    const verifyCredBtn = page.getByRole("button", { name: "Verify credential" });
    await verifyCredBtn.click();

    await expect(page.getByText("DPDP Consent Protocol Required")).toBeVisible({
      timeout: 10000,
    });
    await expect(
      page.getByText(`12-Digit Student APAAR ID Entered (${studentApaarId})`)
    ).toBeVisible();
  });
});
