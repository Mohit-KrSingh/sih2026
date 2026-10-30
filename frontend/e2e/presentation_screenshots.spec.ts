import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import path from "path";
import fs from "fs";

/**
 * Task R16: Presentation Assets & PPT Screenshots
 * Captures clean, high-resolution 1280x800 desktop screenshots matching the running app:
 * 1. home.png
 * 2. activate.png
 * 3. upload-result.png
 * 4. validation-flags.png
 * 5. college-dashboard.png
 * 6. aicte-overview.png
 * 7. compliance.png
 * 8. anomalies.png
 * 9. verify-consent.png
 */

const SCREENSHOT_DIR = path.resolve(
  process.cwd().endsWith("frontend") ? path.resolve(process.cwd(), "..") : process.cwd(),
  "docs",
  "screens"
);

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

test.describe("R16: Presentation Screenshots for Team PPT", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test.beforeEach(async () => {
    try {
      const rootDir = process.cwd().endsWith("frontend")
        ? path.resolve(process.cwd(), "..")
        : process.cwd();
      const resetCmd = `"${path.join(
        rootDir,
        ".venv/Scripts/python.exe"
      )}" -c "import sys; sys.path.insert(0, 'backend'); from app.db import get_redis; r = next(get_redis()); keys = r.keys('ratelimit:*'); (r.delete(*keys) if keys else None)"`;
      execSync(resetCmd, { cwd: rootDir });
    } catch (e) {
      console.warn("Rate limit reset warning:", e);
    }
  });

  async function loginAsCollege(page: any, email = "admin@mmit-mumbai.ac.in") {
    await page.goto("/login/college");
    await page.getByLabel("Official Institutional Email").fill(email);
    await page.getByLabel("Password").fill("Demo@12345");
    await page.getByRole("button", { name: "Sign in as college" }).click();

    const mfaInput = page.getByLabel("Authenticator Code");
    if (await mfaInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await mfaInput.fill("123456");
      await page.getByRole("button", { name: /Verify and sign in|Verify code|Verify MFA/i }).click();
    }

    await page.waitForURL("**/college/dashboard", { timeout: 15000 });
  }

  async function loginAsAicteOfficer(page: any) {
    await page.goto("/login/aicte");
    await page.getByLabel("Official AICTE Email").fill("aicte_officer@aicte-india.org");
    await page.getByLabel("Password").fill("Demo@12345");
    await page.getByRole("button", { name: "Sign in to AICTE portal" }).click();

    const mfaInput = page.getByLabel("Authenticator Code");
    if (await mfaInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await mfaInput.fill("123456");
      await page.getByRole("button", { name: /Verify and sign in|Verify code|Verify MFA/i }).click();
    }

    await page.waitForURL("**/aicte/**", { timeout: 15000 });
  }

  test("1. home screenshot", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("Verified student records for every AICTE college");
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "home.png"), fullPage: false });
  });

  test("2. activate screenshot", async ({ page }) => {
    await page.goto("/activate");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("Activate Your Institution Account");
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "activate.png"), fullPage: false });
  });

  test("3. upload result screenshot", async ({ page }) => {
    await loginAsCollege(page, "admin@ngec-nagpur.gov.in");
    await page.goto("/college/upload");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("Bulk Student Enrolment Upload");

    // Upload test CSV
    const testCsv = [
      "apaar_id,name,dob,gender,course,branch,admission_year,enrolment_no,admission_date,admission_mode,seat_type,reservation_category,nri,oci,foreign_national,country",
      "100000003001,Devendra Singh,2002-09-05,Male,Mechanical Engineering,Mechanical,2026-27,ENR-ME-01,2026-07-15,State counselling,Regular,General,No,No,No,",
      "900011112222,Aaditya Patil,2004-05-10,Male,Mechanical Engineering,Mechanical,2026-27,ENR-ME-02,2026-07-15,State counselling,Regular,General,No,No,No,",
      "100000003003,Bad$Name99,2028-01-01,Other,Mechanical Engineering,Mechanical,2026-27,ENR-ME-03,2026-07-15,State counselling,Regular,General,No,No,No,",
    ].join("\n");

    await page.locator("#file-upload").setInputFiles({
      name: "demo_upload.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(testCsv),
    });

    await page.getByRole("button", { name: "Upload & Run Validation Engine" }).click();
    await expect(page.getByText("Total Uploaded")).toBeVisible({ timeout: 15000 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "upload-result.png"), fullPage: false });
  });

  test("4. validation flags screenshot", async ({ page }) => {
    await loginAsCollege(page, "admin@mmit-mumbai.ac.in");
    await page.goto("/college/validation");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("Validation Flags & Justifications");
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "validation-flags.png"), fullPage: false });
  });

  test("5. college dashboard screenshot", async ({ page }) => {
    await loginAsCollege(page, "admin@mmit-mumbai.ac.in");
    await page.goto("/college/dashboard");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("Institutional Dashboard");
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "college-dashboard.png"), fullPage: false });
  });

  test("6. aicte overview screenshot", async ({ page }) => {
    await loginAsAicteOfficer(page);
    await page.goto("/aicte/overview");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("Central Oversight & Analytics Dashboard");
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "aicte-overview.png"), fullPage: false });
  });

  test("7. compliance screenshot", async ({ page }) => {
    await loginAsAicteOfficer(page);
    await page.goto("/aicte/compliance");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("Over-Intake Compliance & Red List");
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "compliance.png"), fullPage: false });
  });

  test("8. anomalies screenshot", async ({ page }) => {
    await loginAsAicteOfficer(page);
    await page.goto("/aicte/anomalies");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("Intelligent Anomaly Detection");
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "anomalies.png"), fullPage: false });
  });

  test("9. verify consent screenshot", async ({ page }) => {
    await page.goto("/verify?vid=VR-2025-111122223333");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("Verify Student Academic Credential");
    await expect(page.getByText("Cryptographically Valid Credential")).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "verify-consent.png"), fullPage: false });
  });
});
