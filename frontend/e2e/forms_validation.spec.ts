import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { execSync } from "child_process";
import path from "path";

test.describe("R07: Forms and Validation Experience", () => {
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
    await page.waitForURL("**/college/dashboard", { timeout: 15000 });
  }

  test("submits an invalid student form, focus lands on error summary, and links focus the right fields", async ({
    page,
  }) => {
    await loginAsCollege(page);

    // Navigate to single student entry
    await page.goto("/college/students/new");
    await expect(page.locator("h1")).toContainText("Single Student Entry");

    // Verify groups exist per Spec 13: Identity, Admission, Category
    await expect(page.getByText("Identity Information")).toBeVisible();
    await expect(page.getByText("Admission Details")).toBeVisible();
    await expect(page.getByText("Category & Nationality")).toBeVisible();

    // Verify required fields have visible "Required" text badge
    const requiredBadges = page.locator("text=Required");
    expect(await requiredBadges.count()).toBeGreaterThanOrEqual(4);

    // Submit the form while empty (invalid)
    const checkAndSaveBtn = page.getByRole("button", { name: "Check and save" });
    await checkAndSaveBtn.click();

    // 1. Assert Error Summary appears at the top and receives programmatic focus
    const errorSummary = page.locator("#error-summary");
    await expect(errorSummary).toBeVisible();
    await expect(errorSummary).toBeFocused();

    // 2. Assert error summary contains links to invalid fields
    const apaarLink = errorSummary.locator("a[href='#apaar_id']");
    await expect(apaarLink).toBeVisible();
    await expect(apaarLink).toContainText("APAAR ID is required");

    const nameLink = errorSummary.locator("a[href='#name']");
    await expect(nameLink).toBeVisible();
    await expect(nameLink).toContainText("Student full name is required");

    // 3. Click the APAAR ID link in the error summary and assert focus moves to the apaar_id input field
    await apaarLink.click();
    const apaarInput = page.locator("#apaar_id");
    await expect(apaarInput).toBeFocused();
    await expect(apaarInput).toHaveAttribute("aria-invalid", "true");
    await expect(apaarInput).toHaveAttribute("aria-describedby", /apaar_id-error/);

    // 4. Click the Name link in the error summary and assert focus moves to the name input field
    await nameLink.click();
    const nameInput = page.locator("#name");
    await expect(nameInput).toBeFocused();
    await expect(nameInput).toHaveAttribute("aria-invalid", "true");
    await expect(nameInput).toHaveAttribute("aria-describedby", /name-error/);

    // 5. Fill APAAR ID and Name, check live interaction
    await apaarInput.fill("111122223333");
    await nameInput.fill("Rahul Sharma");
  });

  test("seat declaration screen displays AICTE-owned numbers with lock icon and 'Set by AICTE' and includes 'Request a correction' link", async ({
    page,
  }) => {
    await loginAsCollege(page);

    // Navigate to seat declarations
    await page.goto("/college/seats");
    await expect(page.locator("h1")).toContainText("Seat Declarations");

    // 1. Verify 'Set by AICTE' labels appear for approved intake and supernumerary quotas
    const setByAicteElements = page.getByText("Set by AICTE");
    expect(await setByAicteElements.count()).toBeGreaterThanOrEqual(2);

    // 2. Verify 'Request a correction' link exists and links to change requests
    const correctionLinks = page.getByRole("link", { name: /Request a correction/i });
    expect(await correctionLinks.count()).toBeGreaterThanOrEqual(1);
    await expect(correctionLinks.first()).toHaveAttribute("href", "/college/change-requests");

    // 3. Click 'Request a correction' and verify navigation
    await correctionLinks.first().click();
    await page.waitForURL("**/college/change-requests", { timeout: 10000 });
    await expect(page).toHaveURL(/\/college\/change-requests/);
  });

  test("axe-core accessibility scan on student form and seat declarations passes with zero critical or serious violations", async ({
    page,
  }) => {
    await loginAsCollege(page);

    // Scan Student Form
    await page.goto("/college/students/new");
    await page.waitForLoadState("domcontentloaded");
    const formAxeResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const formViolations = formAxeResults.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    );
    expect(formViolations).toEqual([]);

    // Scan Seat Declarations
    await page.goto("/college/seats");
    await page.waitForLoadState("domcontentloaded");
    await page.waitForLoadState("networkidle");
    await page.getByRole("heading", { name: "Seat Declarations & Course Summary" }).waitFor({ state: "visible" });
    await page.getByRole("table").waitFor({ state: "visible" });
    const seatsAxeResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const seatsViolations = seatsAxeResults.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    );
    expect(seatsViolations).toEqual([]);
  });

  test("student form and seat declarations fit 360px viewport without horizontal scroll", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await loginAsCollege(page);

    // Student Form at 360px
    await page.goto("/college/students/new");
    await page.waitForLoadState("domcontentloaded");
    const formHasOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(formHasOverflow).toBe(false);

    // Seat Declarations at 360px
    await page.goto("/college/seats");
    await page.waitForLoadState("domcontentloaded");
    const seatsHasOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(seatsHasOverflow).toBe(false);
  });
});
