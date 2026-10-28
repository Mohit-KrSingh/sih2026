import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import path from "path";

test.describe("T39: End-to-End Golden Path Smoke Test", () => {
  // Test target: South Delhi Polytechnic & Engineering Academy (1-10000028)
  const targetAicteId = "1-10000028";
  const collegeEmail = "principal@sdpea-delhi.ac.in";
  const officerEmail = "aicte_officer@aicte-india.org";
  const officerPassword = "Demo@12345";
  const verifierEmail = "verifier@tcs-verifications.com";
  const verifierPassword = "Demo@12345";
  const studentApaarId = "555566667777";
  const purposeText = "TCS Campus Hiring 2026 Academic Credential Verification";

  const rootDir = process.cwd().endsWith("frontend") ? path.resolve(process.cwd(), "..") : process.cwd();
  const pythonBin = path.join(rootDir, ".venv/Scripts/python.exe");

  // Increase timeout for the full 9-step cross-role golden path
  test.setTimeout(180000);

  test.beforeEach(async () => {
    // Reset target institution to not_activated and remove previous test artifacts
    try {
      execSync(
        `"${pythonBin}" scripts/reset_college.py --aicte-id "${targetAicteId}" --apaar-id "${studentApaarId}"`,
        { cwd: rootDir }
      );
    } catch (e) {
      console.warn("Golden path beforeEach reset warning:", e);
    }
  });

  test("runs the full end-to-end golden path across all 9 milestones", async ({
    page,
    request,
  }) => {
    // =========================================================================
    // STEP 1: Activate college via /activate and approve via AICTE Officer
    // =========================================================================
    await page.goto("/activate");
    await expect(page.locator("h1")).toContainText("Activate Your Institution Account");

    // Enter AICTE ID and verify institution
    await page.getByLabel("AICTE Institute Identifier").fill(targetAicteId);
    await page.getByRole("button", { name: "Verify institution" }).click();

    // Confirm master match banner
    await expect(page.getByText("Institution Verified in AICTE Master Directory")).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByText("South Delhi Polytechnic & Engineering Academy")).toBeVisible();

    // Request activation OTP
    await page.getByRole("button", { name: "Send OTP to official contact" }).click();
    await expect(page.getByText("Step 2: Enter Verification Code")).toBeVisible({ timeout: 10000 });

    // Retrieve OTP from dev outbox
    await page.waitForTimeout(1000);
    const outboxResp1 = await request.get("http://127.0.0.1:8000/api/v1/dev/outbox");
    expect(outboxResp1.ok()).toBeTruthy();
    const outboxData1 = await outboxResp1.json();
    const matchedMsg1 = outboxData1
      .filter((m: { body: string; recipient: string }) =>
        m.body.includes("verification code") || m.recipient.includes("sdpea-delhi")
      )
      .sort(
        (a: { created_at: string }, b: { created_at: string }) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )[0];
    expect(matchedMsg1).toBeDefined();
    const otpMatch1 = matchedMsg1.body.match(/\b\d{6}\b/);
    expect(otpMatch1).not.toBeNull();
    const activationOtp = otpMatch1[0];

    // Submit OTP
    await page.getByLabel("6-Digit Verification Code").fill(activationOtp);
    await page.getByRole("button", { name: "Verify OTP code" }).click();

    // Step 3: Signatory Verification & Letter
    await expect(
      page.getByText("Step 3: Authorized Signatory Verification & Letter")
    ).toBeVisible({ timeout: 10000 });
    await expect(page.getByLabel("Authorized Signatory Name")).toHaveValue(/Dr\. Neeraj Malik/);

    // Upload authorization letter
    await page.locator("#letter-file-input").setInputFiles({
      name: "sdpea_official_letter.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 Mock Official Institution Authorization Letter"),
    });

    // Check declaration checkbox and submit
    await page.locator("#declaration-cb").check();
    await page.getByRole("button", { name: "Submit activation claim" }).click();

    // Confirm submission
    await expect(page.getByText("Activation Claim Successfully Submitted")).toBeVisible({
      timeout: 15000,
    });

    // AICTE Officer approves the activation claim
    await page.goto("/login/aicte");
    await page.getByLabel("Official AICTE Email").fill(officerEmail);
    await page.getByLabel("Password").fill(officerPassword);
    await page.getByRole("button", { name: "Sign in to AICTE portal" }).click();
    await page.waitForURL("**/aicte/**", { timeout: 10000 });

    // Navigate to Approvals Queue
    await page.goto("/aicte/approvals");
    await expect(page.getByText("Institution Approvals Queue")).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText("South Delhi Polytechnic & Engineering Academy")
    ).toBeVisible({ timeout: 10000 });

    // Open review modal
    const reviewBtn = page
      .getByRole("row", { name: new RegExp(targetAicteId) })
      .getByRole("button", { name: "Review claim" });
    await reviewBtn.click();

    await expect(page.getByText("Institution Activation Review")).toBeVisible();
    await page.getByRole("button", { name: "Approve claim" }).click();
    await page.getByRole("button", { name: "Confirm approval" }).click();

    // Capture temporary password and MFA secret seed from modal
    await expect(page.getByText("Institution Claim Approved")).toBeVisible({ timeout: 10000 });
    const tempPasswordText = await page
      .locator("text=Initial Temporary Password:")
      .locator("..")
      .locator("span.font-mono")
      .textContent();
    const mfaSecretText = await page
      .locator("text=MFA Secret Seed:")
      .locator("..")
      .locator("span.font-mono")
      .textContent();

    expect(tempPasswordText).toBeTruthy();
    expect(mfaSecretText).toBeTruthy();
    const tempPassword = tempPasswordText!.trim();
    const mfaSecret = mfaSecretText!.trim();

    await page.getByRole("button", { name: "Done" }).click();

    // =========================================================================
    // STEP 2: Log in as newly activated college administrator with MFA
    // =========================================================================
    await page.evaluate(() => localStorage.clear());
    await page.goto("/login/college");
    await expect(page.locator("h1")).toContainText("College Portal Login");

    await page.getByLabel("Official Institutional Email").fill(collegeEmail);
    await page.getByLabel("Password").fill(tempPassword);
    await page.getByRole("button", { name: "Sign in as college" }).click();

    // Confirm MFA step appears
    await expect(page.getByText("Two-Factor Authentication Required")).toBeVisible({
      timeout: 10000,
    });

    // Compute TOTP code from secret using pyotp
    const totpCode = execSync(
      `"${pythonBin}" -c "import pyotp; print(pyotp.TOTP('${mfaSecret}').now())"`,
      { cwd: rootDir }
    )
      .toString()
      .trim();

    await page.getByLabel("Authenticator Code").fill(totpCode);
    await page.getByRole("button", { name: "Verify and sign in" }).click();

    // Confirm redirected to college dashboard
    await page.waitForURL("**/college/dashboard**", { timeout: 10000 });
    await expect(page.locator("h1")).toContainText("Institutional Dashboard");
    await expect(page.getByText(collegeEmail).first()).toBeVisible({ timeout: 10000 });

    // =========================================================================
    // STEP 3: Declare seats for course on /college/seats
    // =========================================================================
    await page.goto("/college/seats");
    await expect(page.locator("h1")).toContainText("Seat Declarations");
    await expect(page.getByText("Computer Science and Engineering")).toBeVisible({ timeout: 10000 });

    // Find the row for Computer Science and Engineering and fill regular admitted = 2
    const cseRow = page.locator("tr").filter({ hasText: "Computer Science and Engineering" });
    const regularInput = cseRow.locator("input[type='number']").first();
    await regularInput.fill("2");

    // Wait for debounced autosave or click Save draft and verify saved state
    await page.waitForTimeout(1000);
    const saveDraftBtn = page.getByRole("button", { name: "Save draft" });
    if (await saveDraftBtn.isEnabled()) {
      await saveDraftBtn.click();
    }
    await expect(page.getByText(/Draft autosaved/i)).toBeVisible({ timeout: 10000 });

    // =========================================================================
    // STEP 4: Upload messy CSV triggering an error and an exception
    // =========================================================================
    await page.goto("/college/upload");
    await expect(page.locator("h1")).toContainText("Bulk Student Enrolment Upload");

    // Construct messy CSV: Row 1 has format error (Rahul123 Sharma), Row 2 has cross-college duplicate exception (555566667777)
    const messyCsvContent = [
      "apaar_id,name,dob,gender,course,branch,admission_year,enrolment_no,admission_date,admission_mode,seat_type,reservation_category,nri,oci,foreign_national,country",
      "100000003000,Rahul123 Sharma,2002-09-05,Male,Computer Science and Engineering,Computer Science,2026-27,SDPEA-001,2026-07-15,State counselling,Regular,General,No,No,No,",
      "555566667777,Priya Patel,2004-11-20,Female,Computer Science and Engineering,Computer Science,2026-27,SDPEA-002,2026-07-15,State counselling,Regular,General,No,No,No,",
    ].join("\n");

    await page.locator("#file-upload").setInputFiles({
      name: "messy_students_golden.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(messyCsvContent),
    });

    await page.getByRole("button", { name: "Upload & Run Validation Engine" }).click();

    // Confirm batch results view with error and exception flags
    await expect(page.getByText("Total Uploaded")).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("button", { name: "Error 1" })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole("button", { name: "Exception 1" })).toBeVisible({ timeout: 10000 });

    // Expand details to view the rule code
    await page.getByRole("button", { name: "Details" }).first().click();
    await expect(page.getByText("NAME_FORMAT")).toBeVisible({ timeout: 10000 });

    // =========================================================================
    // STEP 5: Fix errors via inline edit on /college/upload
    // =========================================================================
    const rowWithError = page.locator("tr").filter({ hasText: "100000003000" });
    await rowWithError.getByRole("button", { name: "Inline Edit" }).click();

    // Correct name to registry name 'Nachiket Sehgal'
    const nameEditInput = rowWithError.locator("input[type='text']").first();
    await nameEditInput.fill("Nachiket Sehgal");
    await rowWithError.getByRole("button", { name: "Save & Re-validate" }).click();

    // Confirm inline save success and resolved state
    await expect(page.getByText(/updated and re-validated/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Valid").first()).toBeVisible({ timeout: 10000 });

    // =========================================================================
    // STEP 6: Justify exception on /college/validation
    // =========================================================================
    await page.goto("/college/validation");
    await expect(page.locator("h1")).toContainText("Validation Flags & Justifications");

    // Locate the DUP_SAME_COURSE_OTHER_COLLEGE exception row
    const excFlagRow = page.locator("tr").filter({ hasText: "DUP_SAME_COURSE_OTHER_COLLEGE" });
    await expect(excFlagRow).toBeVisible({ timeout: 10000 });
    await excFlagRow.getByRole("button", { name: "Add Justification" }).click();

    // Modal opens: type justification and attach document PDF
    await expect(page.getByText("Official Justification Statement")).toBeVisible({ timeout: 10000 });
    await page
      .locator("textarea")
      .fill(
        "Inter-state dual credit transfer arrangement approved under AICTE circular ref AICTE/2026/TR-881."
      );

    await page.locator("input[type='file']").setInputFiles({
      name: "dual_credit_approval.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 Mock Official Dual Credit Sanction Order"),
    });

    await page.getByRole("button", { name: "Save Justification" }).click();
    await expect(page.getByText(/Justification submitted successfully/i)).toBeVisible({
      timeout: 10000,
    });
    await expect(excFlagRow.getByText("Justified")).toBeVisible({ timeout: 10000 });

    // =========================================================================
    // STEP 7: Submit data on /college/submit
    // =========================================================================
    await page.goto("/college/submit");
    await expect(page.locator("h1")).toContainText("Final Data Submission");

    // Verify zero blockers and allowed status
    await expect(
      page.getByText("Submit Gate Passed: Ready for Final Submission")
    ).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Submitted with Exceptions")).toBeVisible();

    // Request declaration OTP
    await page.getByRole("button", { name: "Request Declaration OTP" }).click();
    await expect(page.getByText(/Verification OTP delivered to/i)).toBeVisible({ timeout: 10000 });

    // Retrieve declaration OTP from dev outbox
    await page.waitForTimeout(1000);
    const outboxResp2 = await request.get(
      `http://127.0.0.1:8000/api/v1/dev/outbox?recipient=${collegeEmail}`
    );
    expect(outboxResp2.ok()).toBeTruthy();
    const outboxData2 = await outboxResp2.json();
    const otpMatch2 = outboxData2[0].body.match(/\b\d{6}\b/);
    expect(otpMatch2).not.toBeNull();
    const submitOtp = otpMatch2[0];

    // Affirm statutory declaration and input OTP
    await page.locator("input[type='checkbox']").check();
    await page.locator("#otp-input").fill(submitOtp);

    // Click submit button
    await page.getByRole("button", { name: /Submit & Lock Data/i }).click();

    // Confirm receipt and locked state
    await expect(page.getByText("Official AICTE Submission Receipt")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/REC-2026-27/)).toBeVisible();
    await expect(page.getByText(/submitted with exceptions/i)).toBeVisible();

    // =========================================================================
    // STEP 8: AICTE Officer reviews and accepts submission
    // =========================================================================
    await page.evaluate(() => localStorage.clear());
    await page.goto("/login/aicte");
    await page.getByLabel("Official AICTE Email").fill(officerEmail);
    await page.getByLabel("Password").fill(officerPassword);
    await page.getByRole("button", { name: "Sign in to AICTE portal" }).click();
    await page.waitForURL("**/aicte/**", { timeout: 10000 });

    await page.goto("/aicte/review");
    await expect(page.locator("h1")).toContainText("AICTE Submission Review Queue");
    await expect(
      page.getByText("South Delhi Polytechnic & Engineering Academy")
    ).toBeVisible({ timeout: 15000 });

    // Open review item for this institution
    const collegeReviewRow = page
      .locator("tr")
      .filter({ hasText: "South Delhi Polytechnic & Engineering Academy" });
    await collegeReviewRow.getByRole("button", { name: "Review Item" }).click();

    await expect(page.getByText("Take Review Action")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("DUP_SAME_COURSE_OTHER_COLLEGE").first()).toBeVisible();

    // Select Accept Exception radio option
    await page.locator("input[value='accept']").check();
    await page
      .locator("textarea")
      .fill("Dual transfer documentation and AICTE circular verified; exception approved.");

    await page.getByRole("button", { name: "Accept & Resolve Exceptions" }).click();
    await expect(page.getByText(/successfully accepted and resolved/i)).toBeVisible({ timeout: 10000 });

    // Close review modal
    await page.getByRole("button", { name: "Close", exact: true }).click();

    // =========================================================================
    // STEP 9: Verifier checks with student consent
    // =========================================================================
    // 9a: Verifier requests consent on /verifier/search
    await page.evaluate(() => localStorage.clear());
    await page.goto("/login/college");
    const verifierBtn = page.getByText("Tata Consultancy Services (Verifier)");
    await verifierBtn.click();
    await page.getByRole("button", { name: "Sign in as college" }).click();

    await page.waitForURL("**/verifier/search**", { timeout: 10000 });
    await expect(page.locator("h1")).toContainText("Stakeholder Credential Verification");

    await page.getByLabel("Student 12-Digit APAAR ID").fill(studentApaarId);
    await page.getByLabel("Verification Purpose (DPDP Compliance)").fill(purposeText);
    await page.getByRole("button", { name: "Request student consent" }).click();

    await expect(page.getByText("Consent Request #")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("24-Hour Expiry Window")).toBeVisible();

    // 9b: Student authenticates and approves consent on /student
    await page.evaluate(() => localStorage.clear());
    await page.goto("/student");
    await expect(page.locator("h1")).toContainText("Student Consent & Record Portal");

    await page.getByLabel("APAAR Identification Number").fill(studentApaarId);
    await page.getByRole("button", { name: "Send verification OTP" }).click();
    await expect(page.getByText("Step 2: Enter Verification OTP")).toBeVisible({ timeout: 10000 });

    // Retrieve student OTP from dev outbox
    await page.waitForTimeout(1000);
    const studentOutbox = await request.get(
      `http://127.0.0.1:8000/api/v1/dev/outbox?recipient=${studentApaarId}`
    );
    expect(studentOutbox.ok()).toBeTruthy();
    const studentOutboxData = await studentOutbox.json();
    const studentOtpMatch = studentOutboxData[0].body.match(/\b\d{6}\b/);
    expect(studentOtpMatch).not.toBeNull();
    const studentOtp = studentOtpMatch[0];

    await page.getByLabel("6-Digit OTP").fill(studentOtp);
    await page.getByRole("button", { name: "Access records" }).click();

    // Verify student name and records in student portal
    await expect(page.getByText("Priya Patel")).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText("Tata Consultancy Services - Background Verifications").first()
    ).toBeVisible({ timeout: 10000 });

    // Approve consent
    await page.getByRole("button", { name: "Approve consent" }).first().click();
    await expect(page.getByText(/Consent approved/i)).toBeVisible({ timeout: 10000 });

    // 9c: Verifier accesses consented student record with minimal fields
    await page.evaluate(() => localStorage.clear());
    await page.goto("/login/college");
    await page.getByLabel("Official Institutional Email").fill(verifierEmail);
    await page.getByLabel("Password").fill(verifierPassword);
    await page.getByRole("button", { name: "Sign in as college" }).click();
    await page.waitForURL("**/verifier/search**", { timeout: 10000 });

    // Navigate to Verifier History
    await page.goto("/verifier/history");
    await expect(page.locator("h1")).toContainText("Verification & Consent History");
    await expect(page.getByText(purposeText).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Approved").first()).toBeVisible({ timeout: 10000 });

    // Open consented record
    await page.getByRole("button", { name: "View record" }).first().click();

    // Verify Consented Academic Verification Modal details
    await expect(page.getByText("Consented Academic Verification")).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText(/Pune Institute of Advanced Engineering & Technology|Mumbai Metropolitan Institute of Technology|South Delhi Polytechnic & Engineering Academy/i)
    ).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Zero PII Guaranteed/i)).toBeVisible();
    await expect(page.getByText(/VR-2026-/)).toBeVisible();

    // Close modal
    await page.getByRole("button", { name: "Close", exact: true }).click();
  });
});
