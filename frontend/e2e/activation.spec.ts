import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import path from "path";

test.describe("T11: End-to-End College Activation and AICTE Approval Smoke Test", () => {
  const targetAicteId = "1-10000027";

  test.beforeEach(async () => {
    // Reset target institution to not_activated and clear rate limits before test run
    try {
      const rootDir = path.resolve(process.cwd(), "..");
      const resetCmd = `"${path.join(rootDir, ".venv/Scripts/python.exe")}" -c "import sys; sys.path.insert(0, 'backend'); from app.db import SessionLocal, get_redis; from app.models import ActivationRequest, Institution, User; from app.auth.rate_limiter import reset_rate_limit; r = next(get_redis()); reset_rate_limit(r, 'activation_otp'); db = SessionLocal(); inst = db.query(Institution).filter_by(aicte_id='${targetAicteId}').first(); db.query(ActivationRequest).filter_by(institution_id=inst.id).delete(); db.query(User).filter_by(institution_id=inst.id).delete(); inst.account_status = 'not_activated'; db.commit()"`;
      execSync(resetCmd, { cwd: rootDir });
    } catch (e) {
      console.warn("Institution reset warning:", e);
    }
  });

  test("activates a seeded college end to end and approves via AICTE officer queue", async ({
    page,
    request,
  }) => {
    // 1. Visit the institution activation portal
    await page.goto("/activate");
    await expect(page.locator("h1")).toContainText("Activate Your Institution Account");

    // 2. Step 1: Input AICTE ID and verify institution in master directory
    const idInput = page.getByLabel("AICTE Institute Identifier");
    await idInput.fill(targetAicteId);

    const verifyInstBtn = page.getByRole("button", { name: "Verify institution" });
    await verifyInstBtn.click();

    // Confirm master match banner appears
    await expect(
      page.getByText("Institution Verified in AICTE Master Directory"),
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText("Varanasi Engineering & Management Institute"),
    ).toBeVisible();

    // 3. Initiate OTP dispatch to official on-file contacts
    const sendOtpBtn = page.getByRole("button", { name: "Send OTP to official contact" });
    await sendOtpBtn.click();

    // 4. Step 2: Verification Code screen
    await expect(page.getByText("Step 2: Enter Verification Code")).toBeVisible({
      timeout: 10000,
    });

    // Fetch the dispatched OTP from dev outbox API
    let otpCode = "";
    await page.waitForTimeout(1000);
    const outboxResp = await request.get("http://127.0.0.1:8000/api/v1/dev/outbox");
    expect(outboxResp.ok()).toBeTruthy();
    const outboxData = await outboxResp.json();

    const matchedMsg = outboxData
      .filter((m: { body: string; recipient: string }) =>
        m.body.includes("verification code") || m.recipient.includes("vemi-varanasi"),
      )
      .sort(
        (a: { created_at: string }, b: { created_at: string }) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      )[0];

    expect(matchedMsg).toBeDefined();
    const match = matchedMsg.body.match(/\b\d{6}\b/);
    expect(match).not.toBeNull();
    otpCode = match ? match[0] : "";
    expect(otpCode).toHaveLength(6);

    // Enter the OTP code
    const otpInput = page.getByLabel("6-Digit Verification Code");
    await otpInput.fill(otpCode);

    const verifyOtpBtn = page.getByRole("button", { name: "Verify OTP code" });
    await verifyOtpBtn.click();

    // 5. Step 3: Authorized Signatory Verification & Letter
    await expect(
      page.getByText("Step 3: Authorized Signatory Verification & Letter"),
    ).toBeVisible({ timeout: 10000 });

    // Verify signatory name is populated
    const signatoryInput = page.getByLabel("Authorized Signatory Name");
    await expect(signatoryInput).toHaveValue(/Dr\. Rakesh Pandey/);

    // Attach sample authorization letter file
    const fileChooserPromise = page.waitForEvent("filechooser").catch(() => null);
    await page.locator("label[for='letter-file-input']").click();
    const fileChooser = await fileChooserPromise;

    if (fileChooser) {
      await fileChooser.setFiles({
        name: "varanasi_activation_authorization.pdf",
        mimeType: "application/pdf",
        buffer: Buffer.from("%PDF-1.4 Mock Official Authorization Letter Header"),
      });
    } else {
      await page.locator("#letter-file-input").setInputFiles({
        name: "varanasi_activation_authorization.pdf",
        mimeType: "application/pdf",
        buffer: Buffer.from("%PDF-1.4 Mock Official Authorization Letter Header"),
      });
    }

    // Acknowledge statutory declaration
    const declarationCheckbox = page.locator("#declaration-cb");
    await declarationCheckbox.check();

    // Submit the claim
    const submitClaimBtn = page.getByRole("button", { name: "Submit activation claim" });
    await submitClaimBtn.click();

    // 6. Step 4: Claim Confirmation Screen
    await expect(
      page.getByText("Activation Claim Successfully Submitted"),
    ).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/REQ-/)).toBeVisible();
    await expect(page.getByText(targetAicteId)).toBeVisible();

    // 7. AICTE Officer Reviews & Approves Claim
    await page.goto("/login/aicte");
    await expect(page.getByText("AICTE Central Portal")).toBeVisible();

    // Sign in with officer demo credentials
    await page.getByLabel("Official AICTE Email").fill("aicte_officer@aicte-india.org");
    await page.getByLabel("Password").fill("Demo@12345");
    await page.getByRole("button", { name: "Sign in to AICTE portal" }).click();

    // Wait for authentication & redirect to overview
    await page.waitForURL("**/aicte/**", { timeout: 10000 });

    // Navigate to Approvals Queue
    await page.goto("/aicte/approvals");
    await expect(page.getByText("Institution Approvals Queue")).toBeVisible({ timeout: 10000 });

    // Ensure our college appears in the table
    await expect(
      page.getByText("Varanasi Engineering & Management Institute"),
    ).toBeVisible({ timeout: 10000 });

    // Open review modal for this request
    const reviewBtn = page
      .getByRole("row", { name: new RegExp(targetAicteId) })
      .getByRole("button", { name: "Review claim" });
    await reviewBtn.click();

    await expect(page.getByText("Institution Activation Review")).toBeVisible();

    // Click Approve
    const modalApproveBtn = page.getByRole("button", { name: "Approve claim" });
    await modalApproveBtn.click();

    // Confirm approval in form
    const confirmApproveBtn = page.getByRole("button", { name: "Confirm approval" });
    await confirmApproveBtn.click();

    // Verify approval confirmation and created credentials
    await expect(page.getByText("Institution Claim Approved")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Enforced", { exact: true })).toBeVisible();

    const doneBtn = page.getByRole("button", { name: "Done" });
    await doneBtn.click();

    // 8. Public Status Tracker Verification
    await page.goto("/activate");
    const checkStatusTab = page.getByRole("button", { name: "Check claim status" });
    await checkStatusTab.click();

    const statusIdInput = page.getByLabel("AICTE Institute Identifier");
    await statusIdInput.fill(targetAicteId);

    const checkStatusBtn = page.getByRole("button", { name: "Check status" });
    await checkStatusBtn.click();

    await expect(
      page.getByText("Account: active"),
    ).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText("This institution account is active. You can log in with administrator credentials."),
    ).toBeVisible();
  });
});
