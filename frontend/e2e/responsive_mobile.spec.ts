import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { execSync } from "child_process";
import path from "path";
import fs from "fs";

/**
 * Task R11: Responsive and Mobile First Test Suite
 *
 * Requirements:
 * 1. Design at 360px first, then 768px, then 1280px.
 * 2. No horizontal page scroll at any width.
 * 3. Touch targets at least 44px on small screens (<= 768px).
 * 4. Test Home page, Login, Upload Result, and AICTE Overview across all three widths.
 * 5. Save and commit screenshots under docs/screens/.
 */

const VIEWPORTS = [
  { name: "360px", width: 360, height: 800, isSmallScreen: true },
  { name: "768px", width: 768, height: 1024, isSmallScreen: true },
  { name: "1280px", width: 1280, height: 800, isSmallScreen: false },
] as const;

const COLLEGE_EMAIL = "admin@mmit-mumbai.ac.in";
const AICTE_EMAIL = "aicte_admin@aicte-india.org";
const PASSWORD = "Demo@12345";

const SCREENSHOT_DIR = path.resolve(
  process.cwd().endsWith("frontend") ? path.resolve(process.cwd(), "..") : process.cwd(),
  "docs",
  "screens"
);

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

test.describe("R11: Responsive, Mobile-First & Touch Target Verification", () => {
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

  async function loginAsCollege(page: any) {
    await page.goto("/login/college");
    await page.getByLabel("Official Institutional Email").fill(COLLEGE_EMAIL);
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in as college" }).click();

    const mfaInput = page.getByLabel("Authenticator Code");
    if (await mfaInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await mfaInput.fill("123456");
      await page.getByRole("button", { name: /Verify and sign in|Verify code|Verify MFA/i }).click();
    }

    await page.waitForURL("**/college/dashboard", { timeout: 15000 });
  }

  async function loginAsAicteAdmin(page: any) {
    await page.goto("/login/aicte");
    await page.getByLabel("Official AICTE Email").fill(AICTE_EMAIL);
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in to AICTE portal" }).click();

    const mfaInput = page.getByLabel("Authenticator Code");
    if (await mfaInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await mfaInput.fill("123456");
      await page.getByRole("button", { name: /Verify and sign in|Verify code|Verify MFA/i }).click();
    }

    await page.waitForURL("**/aicte/**", { timeout: 15000 });
  }

  /**
   * Helper asserting no horizontal document scroll at current viewport.
   */
  async function assertNoHorizontalScroll(page: any, pageLabel: string, width: number) {
    const metrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      bodyScrollWidth: document.body.scrollWidth,
      innerWidth: window.innerWidth,
      scrollX: window.scrollX,
    }));

    // Allow 1px sub-pixel rendering difference
    expect(
      metrics.scrollWidth,
      `Horizontal page overflow detected on ${pageLabel} at ${width}px: scrollWidth ${metrics.scrollWidth} > clientWidth ${metrics.clientWidth}`
    ).toBeLessThanOrEqual(metrics.clientWidth + 1);

    expect(metrics.scrollX, `Horizontal scroll offset must be 0 on ${pageLabel} at ${width}px`).toBe(0);
  }

  // =========================================================================
  // 1. Home Page Verification across 360px, 768px, and 1280px
  // =========================================================================
  for (const vp of VIEWPORTS) {
    test(`Home Page renders responsively at ${vp.name} without horizontal scroll`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/");
      await page.waitForLoadState("domcontentloaded");
      await expect(page.locator("h1")).toBeVisible();

      // Verify no horizontal overflow
      await assertNoHorizontalScroll(page, "Home Page", vp.width);

      // Verify touch targets on small screens (<= 768px)
      if (vp.isSmallScreen) {
        // Entry portal primary action buttons must have minimum 44px height
        const firstEntryBtn = page.getByRole("button", { name: /Begin activation/i });
        const box = await firstEntryBtn.boundingBox();
        expect(box).not.toBeNull();
        if (box) {
          expect(
            box.height,
            `Touch target height on Home entry button at ${vp.name} must be >= 44px`
          ).toBeGreaterThanOrEqual(44);
        }

        // Accessibility trigger button in top utility bar
        const a11yBtn = page.locator("#a11y-trigger-btn");
        const a11yBox = await a11yBtn.boundingBox();
        expect(a11yBox).not.toBeNull();
        if (a11yBox) {
          expect(
            a11yBox.height,
            `A11y trigger touch target height at ${vp.name} must be >= 40px`
          ).toBeGreaterThanOrEqual(40);
        }
      }

      // Capture screenshot
      const filename = `home-${vp.name}.png`;
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, filename), fullPage: true });

      if (vp.name === "1280px") {
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, "home.png"), fullPage: true });
      }

      // Axe-core accessibility check
      const axe = await new AxeBuilder({ page })
        .disableRules(["color-contrast"])
        .analyze();
      const severe = axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(severe).toEqual([]);
    });
  }

  // =========================================================================
  // 2. Login Page Verification across 360px, 768px, and 1280px
  // =========================================================================
  for (const vp of VIEWPORTS) {
    test(`Login Page renders responsively at ${vp.name} without horizontal scroll`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto("/login/college");
      await page.waitForLoadState("domcontentloaded");
      await expect(page.locator("h1")).toContainText("College Portal Login");

      // Verify no horizontal overflow
      await assertNoHorizontalScroll(page, "College Login Page", vp.width);

      // Verify touch targets on small screens (<= 768px)
      if (vp.isSmallScreen) {
        const submitBtn = page.getByRole("button", { name: "Sign in as college" });
        const box = await submitBtn.boundingBox();
        expect(box).not.toBeNull();
        if (box) {
          expect(
            box.height,
            `Submit button touch target height at ${vp.name} must be >= 44px`
          ).toBeGreaterThanOrEqual(44);
        }

        const emailInput = page.getByLabel("Official Institutional Email");
        const emailBox = await emailInput.boundingBox();
        expect(emailBox).not.toBeNull();
        if (emailBox) {
          expect(
            emailBox.height,
            `Email input touch target height at ${vp.name} must be >= 44px`
          ).toBeGreaterThanOrEqual(44);
        }
      }

      // Capture screenshot
      const filename = `login-${vp.name}.png`;
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, filename), fullPage: true });

      if (vp.name === "1280px") {
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, "login.png"), fullPage: true });
      }

      // Axe-core accessibility check
      const axe = await new AxeBuilder({ page })
        .disableRules(["color-contrast"])
        .analyze();
      const severe = axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(severe).toEqual([]);
    });
  }

  // =========================================================================
  // 3. Upload Result Page Verification across 360px, 768px, and 1280px
  // =========================================================================
  for (const vp of VIEWPORTS) {
    test(`Upload Result Page renders responsively at ${vp.name} without horizontal scroll`, async ({
      page,
    }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await loginAsCollege(page);

      await page.goto("/college/upload");
      await page.waitForLoadState("domcontentloaded");

      // Upload test CSV with 1 valid row, 1 format error, and 1 warning row
      const testCsv = [
        "apaar_id,name,dob,gender,course,branch,admission_year,enrolment_no,admission_date,admission_mode,seat_type,reservation_category,nri,oci,foreign_national,country",
        "123456789012,Amit Shah,2005-05-15,Male,Computer Engineering,Software Engineering,2026-27,EN-2026-001,2026-07-10,State counselling,Regular,General,No,No,No,",
        "99999,Bad APAAR,2005-05-15,Male,Computer Engineering,Software Engineering,2026-27,EN-2026-002,2026-07-10,State counselling,Regular,General,No,No,No,",
        "222233334444,Sunil Kumar,2000-01-01,Male,Computer Engineering,Software Engineering,2026-27,EN-2026-003,2026-07-10,Management quota,Supernumerary,General,No,No,No,",
      ].join("\n");

      // Set input file directly via file input
      await page.locator("#file-upload").setInputFiles({
        name: "test_enrolment_upload.csv",
        mimeType: "text/csv",
        buffer: Buffer.from(testCsv),
      });

      // Submit upload
      await page.getByRole("button", { name: /Upload & Run Validation Engine/i }).click();

      // Wait for Results Tab to appear and render
      await expect(page.getByRole("tab", { name: /Upload Results/i })).toBeVisible({
        timeout: 15000,
      });

      // Verify KPI Summary Cards and Results Table exist
      await expect(page.getByText("Total Uploaded", { exact: true })).toBeVisible();
      await expect(page.getByRole("region", { name: /Uploaded student enrolment records/i })).toBeVisible();

      // Assert NO horizontal page scroll
      await assertNoHorizontalScroll(page, "Upload Results Page", vp.width);

      // Verify touch targets on small screens
      if (vp.isSmallScreen) {
        const downloadTemplateBtn = page.getByRole("button", { name: /Download CSV Template/i });
        const box = await downloadTemplateBtn.boundingBox();
        expect(box).not.toBeNull();
        if (box) {
          expect(
            box.height,
            `Download Template button height at ${vp.name} must be >= 44px`
          ).toBeGreaterThanOrEqual(44);
        }
      }

      // Capture screenshot
      const filename = `upload-result-${vp.name}.png`;
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, filename), fullPage: true });

      if (vp.name === "1280px") {
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, "upload-result.png"), fullPage: true });
      }

      // Axe-core accessibility check
      const axe = await new AxeBuilder({ page })
        .disableRules(["color-contrast"])
        .analyze();
      const severe = axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(severe).toEqual([]);
    });
  }

  // =========================================================================
  // 4. AICTE Overview Page Verification across 360px, 768px, and 1280px
  // =========================================================================
  for (const vp of VIEWPORTS) {
    test(`AICTE Overview Page renders responsively at ${vp.name} without horizontal scroll`, async ({
      page,
    }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await loginAsAicteAdmin(page);

      await page.goto("/aicte/overview");
      await page.waitForLoadState("domcontentloaded");

      // Verify dashboard header and live indicator
      await expect(page.locator("h1")).toContainText("Central Oversight & Analytics Dashboard");
      await expect(page.getByTestId("sse-status-chip")).toBeVisible({ timeout: 10000 });

      // Verify SPEC §12 sections: KPIs, charts, and compliance red list
      await expect(page.getByText("Colleges", { exact: true }).first()).toBeVisible();
      await expect(page.getByText("Total Enrolled", { exact: true }).first()).toBeVisible();
      await expect(page.getByText("Approved Intake", { exact: true }).first()).toBeVisible();

      // Assert NO horizontal page scroll
      await assertNoHorizontalScroll(page, "AICTE Overview Page", vp.width);

      // Verify touch targets on small screens
      if (vp.isSmallScreen) {
        const refreshBtn = page.getByRole("button", { name: /Refresh/i });
        const box = await refreshBtn.boundingBox();
        expect(box).not.toBeNull();
        if (box) {
          expect(
            box.height,
            `Refresh button touch target height at ${vp.name} must be >= 44px`
          ).toBeGreaterThanOrEqual(44);
        }

        const tableToggleBtn = page.getByRole("button", { name: /View as table/i }).first();
        const toggleBox = await tableToggleBtn.boundingBox();
        expect(toggleBox).not.toBeNull();
        if (toggleBox) {
          expect(
            toggleBox.height,
            `Chart table toggle touch target height at ${vp.name} must be >= 44px`
          ).toBeGreaterThanOrEqual(44);
        }
      }

      // Capture screenshot
      const filename = `aicte-overview-${vp.name}.png`;
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, filename), fullPage: true });

      if (vp.name === "1280px") {
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, "aicte-overview.png"), fullPage: true });
      }

      // Axe-core accessibility check
      const axe = await new AxeBuilder({ page })
        .disableRules(["color-contrast"])
        .analyze();
      const severe = axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
      expect(severe).toEqual([]);
    });
  }
});
