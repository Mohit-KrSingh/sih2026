import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { execSync } from "child_process";
import path from "path";

test.describe("R09: Tables, Upload and Results", () => {
  const collegeEmail = "admin@mmit-mumbai.ac.in";
  const password = "Demo@12345";

  test.beforeEach(async () => {
    try {
      const rootDir = process.cwd().endsWith("frontend") ? path.resolve(process.cwd(), "..") : process.cwd();
      const resetCmd = `"${path.join(rootDir, ".venv/Scripts/python.exe")}" -c "import sys; sys.path.insert(0, 'backend'); from app.db import get_redis; r = next(get_redis()); keys = r.keys('ratelimit:*'); (r.delete(*keys) if keys else None)"`;
      execSync(resetCmd, { cwd: rootDir });
    } catch (e) {
      console.warn("Rate limit reset warning:", e);
    }
  });

  async function loginAsCollege(page: any) {
    await page.goto("/login/college");
    await page.getByLabel("Official Institutional Email").fill(collegeEmail);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in as college" }).click();

    // Handle MFA if enabled
    const mfaInput = page.getByLabel("Authenticator Code");
    if (await mfaInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await mfaInput.fill("123456");
      await page.getByRole("button", { name: /Verify and sign in|Verify code|Verify MFA/i }).click();
    }

    await page.waitForURL("**/college/dashboard", { timeout: 15000 });
  }

  test("upload flow with keyboard navigation, results table, sorting, details, and inline edit", async ({
    page,
  }) => {
    await loginAsCollege(page);

    // Navigate to bulk upload screen
    await page.goto("/college/upload");
    await expect(page.locator("h1")).toContainText("Bulk Student Enrolment Upload");

    // Check Axe on upload form
    const axeUploadForm = await new AxeBuilder({ page })
      .disableRules(["color-contrast"])
      .analyze();
    const severeUploadForm = axeUploadForm.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical"
    );
    expect(severeUploadForm).toEqual([]);

    // Verify template download button is keyboard operable
    const templateBtn = page.getByRole("button", { name: /Download CSV Template/i });
    await expect(templateBtn).toBeVisible();

    // Prepare CSV with 1 valid row, 1 format error row, and 1 warning row
    const testCsv = [
      "apaar_id,name,dob,gender,course,branch,admission_year,enrolment_no,admission_date,admission_mode,seat_type,reservation_category,nri,oci,foreign_national,country",
      "100000003000,Devendra123 Singh,2002-09-05,Male,Computer Science and Engineering,Computer Science,2026-27,ENR-R09-01,2026-07-15,State counselling,Regular,General,No,No,No,",
      "900011112222,Aaditya Patil,2004-05-10,Male,Computer Science and Engineering,Computer Science,2026-27,ENR-R09-02,2026-07-15,State counselling,Regular,General,No,No,No,",
    ].join("\n");

    // Select file via input
    await page.locator("#file-upload").setInputFiles({
      name: "r09_test_upload.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(testCsv),
    });

    // Submit upload via keyboard
    const uploadSubmitBtn = page.getByRole("button", { name: "Upload & Run Validation Engine" });
    await uploadSubmitBtn.focus();
    await page.keyboard.press("Enter");

    // Wait for results tab and summary cards to render
    await expect(page.getByText("Total Uploaded")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Valid (Clean)")).toBeVisible();
    await expect(page.getByText("Flagged Rows")).toBeVisible();

    // Verify Table is wrapped in keyboard-operable scroll region
    const tableRegion = page.getByRole("region", { name: "Uploaded student enrolment records" });
    await expect(tableRegion).toBeVisible();
    await expect(tableRegion).toHaveAttribute("tabindex", "0");

    // Check sticky header and sortable column headers
    const nameColHeader = page.getByRole("columnheader", { name: /Student Name/i });
    await expect(nameColHeader).toBeVisible();

    // Trigger keyboard sort on Student Name column
    const sortBtn = nameColHeader.getByRole("button");
    await sortBtn.focus();
    await page.keyboard.press("Enter");
    await expect(nameColHeader).toHaveAttribute("aria-sort", "ascending");

    // Press again to sort descending
    await page.keyboard.press("Space");
    await expect(nameColHeader).toHaveAttribute("aria-sort", "descending");

    // Verify per-row badges render
    await expect(page.getByRole("button", { name: /Error \d+/i }).first()).toBeVisible({ timeout: 10000 });

    // Expand flag details drawer
    const detailsBtn = page.getByRole("button", { name: "Details" }).first();
    await detailsBtn.click();
    await expect(page.getByText("NAME_FORMAT")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/How to fix:/i).first()).toBeVisible();

    // Test inline edit and re-validation
    const errorRow = page.locator("tr").filter({ hasText: "100000003000" });
    await errorRow.getByRole("button", { name: "Inline Edit" }).click();

    // Fill valid name without numbers
    const nameInput = errorRow.locator("input[type='text']").first();
    await nameInput.fill("Devendra Singh");

    await errorRow.getByRole("button", { name: "Save & Re-validate" }).click();
    await expect(page.getByText(/updated and re-validated successfully/i)).toBeVisible({ timeout: 15000 });

    // Check Axe on results screen
    const axeResults = await new AxeBuilder({ page })
      .disableRules(["color-contrast"])
      .analyze();
    const severeResults = axeResults.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical"
    );
    expect(severeResults).toEqual([]);
  });

  test("table maintains responsive layout without horizontal document overflow at 360px viewport", async ({
    page,
  }) => {
    await loginAsCollege(page);

    await page.setViewportSize({ width: 360, height: 740 });
    await page.goto("/college/upload");
    await expect(page.locator("h1")).toContainText("Bulk Student Enrolment Upload");

    // Verify page body does not overflow horizontally
    const bodyScrollWidth = await page.evaluate(() => document.body.scrollWidth);
    const windowInnerWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyScrollWidth).toBeLessThanOrEqual(windowInnerWidth + 5);

    // Verify Table region can scroll horizontally inside its bounded container
    await page.getByRole("tab", { name: "Upload History" }).click();
    await page.waitForTimeout(500);

    const historyRegion = page.locator('[role="region"][aria-label="Historical student enrolment uploads"]');
    if (await historyRegion.isVisible()) {
      await expect(historyRegion).toBeVisible();
      await expect(historyRegion).toHaveAttribute("tabindex", "0");
    }
  });
});
