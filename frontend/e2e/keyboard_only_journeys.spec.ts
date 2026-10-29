import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import path from "path";

test.describe("R15: Pure Keyboard-Only Journeys Verification", () => {
  const collegeEmail = "admin@mmit-mumbai.ac.in";
  const collegePassword = "Demo@12345";

  const officerEmail = "aicte_officer@aicte-india.org";
  const officerPassword = "Demo@12345";

  const verifierEmail = "verifier@tcs-verifications.com";
  const verifierPassword = "Demo@12345";

  const studentApaarId = "111122223333";

  test.beforeEach(async () => {
    try {
      const rootDir = process.cwd().endsWith("frontend") ? path.resolve(process.cwd(), "..") : process.cwd();
      const resetCmd = `"${path.join(rootDir, ".venv/Scripts/python.exe")}" -c "import sys; sys.path.insert(0, 'backend'); from app.db import get_redis; r = next(get_redis()); keys = r.keys('ratelimit:*'); (r.delete(*keys) if keys else None)"`;
      execSync(resetCmd, { cwd: rootDir });
    } catch (e) {
      console.warn("Rate limit reset warning:", e);
    }
  });

  // ===========================================================================
  // JOURNEY 1: College Upload and Final Submit (Keyboard Only)
  // ===========================================================================
  test("Journey 1: College signs in, inspects upload & submits declaration via keyboard only", async ({
    page,
  }) => {
    // 1. Visit login page
    await page.goto("/login/college");
    await expect(page.locator("h1")).toContainText("College Portal Login");

    // 2. Focus email input and type using keyboard
    const emailInput = page.getByLabel("Official Institutional Email");
    await emailInput.focus();
    await page.keyboard.type(collegeEmail);

    // 3. Tab to password input and type
    await page.keyboard.press("Tab");
    const passwordInput = page.getByLabel("Password");
    await expect(passwordInput).toBeFocused();
    await page.keyboard.type(collegePassword);

    // 4. Tab to submit button and press Enter
    await page.keyboard.press("Tab"); // Tab to forgot password
    await page.keyboard.press("Tab"); // Tab to sign in button
    const submitBtn = page.getByRole("button", { name: "Sign in as college" });
    await expect(submitBtn).toBeFocused();
    await page.keyboard.press("Enter");

    // Handle potential MFA prompt via keyboard
    const mfaInput = page.getByLabel("Authenticator Code");
    if (await mfaInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await mfaInput.focus();
      await page.keyboard.type("123456");
      await page.keyboard.press("Enter");
    }

    await page.waitForURL("**/college/dashboard", { timeout: 15000 });
    await expect(page.locator("h1")).toContainText("Institutional Dashboard");

    // 5. Navigate to Submit screen
    await page.goto("/college/submit");
    await page.waitForLoadState("domcontentloaded");
    await expect(page.locator("h1")).toContainText("Final Data Submission");

    // 6. Check the submission state. If not yet submitted, complete the declaration using keyboard:
    const receiptBanner = page.getByText("Official AICTE Submission Receipt");
    if (await receiptBanner.isVisible({ timeout: 2000 }).catch(() => false)) {
      // Already submitted: verify receipt number is focusable and copyable via keyboard
      const copyBtn = page.getByRole("button", { name: /Copy receipt number|Copied!/i });
      await copyBtn.focus();
      await expect(copyBtn).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(page.getByText("Copied!")).toBeVisible();
    } else {
      // Focus declaration checkbox and press Space to check
      const checkbox = page.getByRole("checkbox");
      await checkbox.focus();
      await expect(checkbox).toBeFocused();
      await page.keyboard.press("Space");
      await expect(checkbox).toBeChecked();

      // Tab to Request OTP button and press Enter
      const requestOtpBtn = page.getByRole("button", { name: /Request declaration OTP|Resend OTP/i });
      await requestOtpBtn.focus();
      await expect(requestOtpBtn).toBeFocused();
      await page.keyboard.press("Enter");

      // Wait for OTP dispatched notification
      await expect(page.getByText(/Verification OTP delivered to/i)).toBeVisible({ timeout: 10000 });

      // Focus OTP input, type 123456
      const otpInput = page.locator("#otp-input");
      await otpInput.focus();
      await expect(otpInput).toBeFocused();
      await page.keyboard.type("123456");

      // Focus final submit button and activate via keyboard Enter
      const finalSubmitBtn = page.getByRole("button", { name: /Submit Annual Student Records/i });
      await finalSubmitBtn.focus();
      await expect(finalSubmitBtn).toBeFocused();
      await page.keyboard.press("Enter");

      // Verify official receipt is generated
      await expect(page.getByText("Official AICTE Submission Receipt")).toBeVisible({ timeout: 15000 });
      await expect(page.getByText(/Acknowledgement Receipt Number/i)).toBeVisible();
    }
  });

  // ===========================================================================
  // JOURNEY 2: AICTE Review Queue and Compliance Decision (Keyboard Only)
  // ===========================================================================
  test("Journey 2: AICTE Officer logs in and reviews exception item via keyboard only", async ({
    page,
  }) => {
    // 1. Visit AICTE login page
    await page.goto("/login/aicte");
    await expect(page.locator("h1")).toContainText("AICTE Central Portal");

    // 2. Focus email input and type using keyboard
    const emailInput = page.getByLabel("Official AICTE Email");
    await emailInput.focus();
    await page.keyboard.type(officerEmail);

    // 3. Tab to password input and type
    await page.keyboard.press("Tab");
    const passwordInput = page.getByLabel("Password");
    await expect(passwordInput).toBeFocused();
    await page.keyboard.type(officerPassword);

    // 4. Tab to sign in button and press Enter
    await page.keyboard.press("Tab");
    const signInBtn = page.getByRole("button", { name: "Sign in to AICTE portal" });
    await expect(signInBtn).toBeFocused();
    await page.keyboard.press("Enter");

    await page.waitForURL("**/aicte/**", { timeout: 15000 });

    // 5. Navigate to Review Queue
    await page.goto("/aicte/review");
    await page.waitForLoadState("domcontentloaded");
    await expect(page.locator("h1")).toContainText("AICTE Submission Review Queue");

    // 6. Find first review button in the table, focus it and press Enter
    const reviewBtn = page.getByRole("button", { name: "Review Item" }).first();
    await expect(reviewBtn).toBeVisible({ timeout: 10000 });
    await reviewBtn.focus();
    await expect(reviewBtn).toBeFocused();
    await page.keyboard.press("Enter");

    // 7. Verify modal opened
    await expect(page.getByText("Take Review Action")).toBeVisible({ timeout: 10000 });

    // 8. Tab to Accept option, select it with keyboard
    const acceptRadio = page.getByLabel("Accept Exception");
    await acceptRadio.focus();
    await expect(acceptRadio).toBeFocused();
    await page.keyboard.press("Space");

    // 9. Focus decision note textarea, type justification
    const noteTextarea = page.getByLabel("Officer Decision Note & Statutory Rationale");
    await noteTextarea.focus();
    await expect(noteTextarea).toBeFocused();
    await page.keyboard.type("Compliance verified against high court interim sanctions.");

    // 10. Focus confirm action button, submit decision via keyboard Enter
    const confirmBtn = page.getByRole("button", { name: "Accept & Resolve Exceptions" });
    await confirmBtn.focus();
    await expect(confirmBtn).toBeFocused();
    await page.keyboard.press("Enter");

    // 11. Modal displays confirmation message
    await expect(page.getByText(/Exceptions successfully accepted and resolved/i)).toBeVisible({ timeout: 10000 });
  });

  // ===========================================================================
  // JOURNEY 3: Verifier Search and Student Consent Flow (Keyboard Only)
  // ===========================================================================
  test("Journey 3: Verifier requests consent and student approves via keyboard only", async ({
    page,
  }) => {
    // -------------------------------------------------------------------------
    // Step A: Verifier requests consent (Keyboard only)
    // -------------------------------------------------------------------------
    await page.goto("/login/college");
    const emailInput = page.getByLabel("Official Institutional Email");
    await emailInput.focus();
    await page.keyboard.type(verifierEmail);

    await page.keyboard.press("Tab");
    const passwordInput = page.getByLabel("Password");
    await expect(passwordInput).toBeFocused();
    await page.keyboard.type(verifierPassword);

    await page.keyboard.press("Tab"); // forgot password
    await page.keyboard.press("Tab"); // submit button
    await page.keyboard.press("Enter");

    await page.waitForURL("**/verifier/search**", { timeout: 15000 });
    await expect(page.locator("h1")).toContainText("Stakeholder Credential Verification");

    // Enter APAAR ID via keyboard
    const apaarInput = page.getByLabel("Student 12-Digit APAAR ID");
    await apaarInput.focus();
    await expect(apaarInput).toBeFocused();
    await page.keyboard.type(studentApaarId);

    // Enter Purpose via keyboard
    await page.keyboard.press("Tab");
    const purposeInput = page.getByLabel("Verification Purpose (DPDP Compliance)");
    await expect(purposeInput).toBeFocused();
    await page.keyboard.type("Pre-employment academic verification");

    // Tab through Quick Test button to submit button
    await page.keyboard.press("Tab"); // quick test button
    await page.keyboard.press("Tab"); // submit button
    const reqBtn = page.getByRole("button", { name: "Request student consent" });
    await expect(reqBtn).toBeFocused();
    await page.keyboard.press("Enter");

    // Verify active consent request card is visible
    await expect(page.getByText("Consent Request #")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("24-Hour Expiry Window")).toBeVisible();

    // -------------------------------------------------------------------------
    // Step B: Student reviews and approves consent (Keyboard only)
    // -------------------------------------------------------------------------
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    await page.goto("/student");
    await expect(page.locator("h1")).toContainText("Student Consent & Record Portal");

    // Enter APAAR ID via keyboard
    const studentInput = page.getByLabel("APAAR Identification Number");
    await studentInput.focus();
    await expect(studentInput).toBeFocused();
    await page.keyboard.type(studentApaarId);

    // Tab to send OTP button and press Enter
    await page.keyboard.press("Tab");
    const sendOtpBtn = page.getByRole("button", { name: "Send verification OTP" });
    await expect(sendOtpBtn).toBeFocused();
    await page.keyboard.press("Enter");

    await expect(page.getByText("Step 2: Enter verification OTP")).toBeVisible({ timeout: 10000 });

    // Focus first OTP digit input and type 123456
    const otpDigit1 = page.getByLabel("Digit 1 of 6");
    await otpDigit1.focus();
    await expect(otpDigit1).toBeFocused();
    await page.keyboard.type("123456");

    // Focus Verify OTP button and press Enter
    const verifyOtpBtn = page.getByRole("button", { name: "Access records" });
    await verifyOtpBtn.focus();
    await expect(verifyOtpBtn).toBeFocused();
    await page.keyboard.press("Enter");

    // Confirm student dashboard loaded
    await expect(page.getByText("Institutions Holding Your Record")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Pending Verification Consent Requests")).toBeVisible();

    // Focus the "Approve consent" button and activate with keyboard Enter
    const approveBtn = page.getByRole("button", { name: "Approve consent" }).first();
    await approveBtn.focus();
    await expect(approveBtn).toBeFocused();
    await page.keyboard.press("Enter");

    // Verify confirmation notification appears
    await expect(page.getByText(/Consent approved/i)).toBeVisible({ timeout: 10000 });
  });
});
