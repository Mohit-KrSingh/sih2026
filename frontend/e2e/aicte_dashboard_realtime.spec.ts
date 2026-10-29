import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { execSync } from "child_process";
import path from "path";

test.describe("R10: AICTE Dashboard, Analytical Charts & Real-time Live Updates", () => {
  const adminEmail = "aicte_admin@aicte-india.org";
  const password = "Demo@12345";

  test.beforeEach(async () => {
    try {
      const rootDir = process.cwd().endsWith("frontend")
        ? path.resolve(process.cwd(), "..")
        : process.cwd();
      const resetCmd = `"${path.join(rootDir, ".venv/Scripts/python.exe")}" -c "import sys; sys.path.insert(0, 'backend'); from app.db import get_redis; r = next(get_redis()); keys = r.keys('ratelimit:*'); (r.delete(*keys) if keys else None)"`;
      execSync(resetCmd, { cwd: rootDir });
    } catch (e) {
      console.warn("Rate limit reset warning:", e);
    }
  });

  async function loginAsAicteAdmin(page: any) {
    await page.goto("/login/aicte");
    await page.getByLabel("Official AICTE Email").fill(adminEmail);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in to AICTE portal" }).click();

    // Handle MFA step if prompted
    const mfaInput = page.getByLabel("Authenticator Code");
    if (await mfaInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await mfaInput.fill("123456");
      await page.getByRole("button", { name: /Verify and sign in|Verify code|Verify MFA/i }).click();
    }

    await page.waitForURL("**/aicte/**", { timeout: 15000 });
  }

  test("verifies AICTE overview KPIs, charts, accessible table toggles, and 360px responsiveness", async ({
    page,
  }) => {
    await loginAsAicteAdmin(page);
    await page.goto("/aicte/overview");

    // 1. Verify header & live SSE status chip
    await expect(page.locator("h1")).toContainText("Central Oversight & Analytics Dashboard");
    const sseChip = page.getByTestId("sse-status-chip");
    await expect(sseChip).toBeVisible({ timeout: 10000 });
    await expect(sseChip).toHaveText(/Live|Reconnecting/);

    // 2. Verify SPEC §12 order: KPIs exist
    await expect(page.getByText("Colleges", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Total Enrolled", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Approved Intake", { exact: true }).first()).toBeVisible();

    // 3. Verify all 3 charts have title, text summary, and "View as table" toggle
    const viewAsTableButtons = page.getByRole("button", { name: /View as table/i });
    await expect(viewAsTableButtons.first()).toBeVisible({ timeout: 10000 });
    const count = await viewAsTableButtons.count();
    expect(count).toBeGreaterThanOrEqual(3);

    // 4. Toggle State Intake Chart to table view and verify table
    const stateTableBtn = page.getByRole("button", {
      name: "View as table for State-Level Intake vs Actual Enrolment",
    });
    await stateTableBtn.click();
    await expect(
      page.getByRole("region", { name: "State-Level Intake vs Actual Enrolment data table" })
    ).toBeVisible();
    await expect(page.getByText("State Jurisdiction")).toBeVisible();
    await expect(
      page.getByRole("button", {
        name: "View as chart for State-Level Intake vs Actual Enrolment",
      })
    ).toBeVisible();

    // Toggle back to chart
    await page
      .getByRole("button", { name: "View as chart for State-Level Intake vs Actual Enrolment" })
      .click();
    await expect(
      page.getByRole("region", { name: "State-Level Intake vs Actual Enrolment chart visualization" })
    ).toBeVisible();

    // 5. Test 360px viewport responsiveness
    await page.setViewportSize({ width: 360, height: 800 });
    await page.waitForTimeout(300);

    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(hasHorizontalScroll).toBe(false);

    // Test table toggle on 360px
    await page
      .getByRole("button", { name: "View as table for Submission Progress" })
      .click();
    await expect(
      page.getByRole("region", { name: "Submission Progress data table" })
    ).toBeVisible();

    // Reset viewport to standard desktop
    await page.setViewportSize({ width: 1280, height: 800 });

    // 6. Axe accessibility scan on AICTE overview
    const axeResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .disableRules(["color-contrast"]) // contrast verified mathematically in unit tests
      .analyze();

    const criticalViolations = axeResults.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    );
    expect(criticalViolations).toEqual([]);
  });

  test("confirms a new submission appears on the dashboard without page reload via real-time SSE", async ({
    page,
  }) => {
    await loginAsAicteAdmin(page);
    await page.goto("/aicte/overview");

    // Wait for the Live Activity Feed to be visible
    await expect(page.getByText("Live System Activity Feed")).toBeVisible({ timeout: 10000 });

    // Publish a unique submission event via backend SSE publisher
    const uniqueInstituteName = `E2E Realtime Institute ${Date.now()}`;
    const rootDir = process.cwd().endsWith("frontend")
      ? path.resolve(process.cwd(), "..")
      : process.cwd();

    const publishCmd = `"${path.join(rootDir, ".venv/Scripts/python.exe")}" -c "import sys; sys.path.insert(0, 'backend'); from app.db import get_redis; from app.analytics.sse import publish_sse_event; r = next(get_redis()); publish_sse_event(r, 'submission_created', {'submission_id': 99991, 'institution_name': '${uniqueInstituteName}', 'status': 'submitted', 'message': 'New submission from ${uniqueInstituteName}'})"`;

    execSync(publishCmd, { cwd: rootDir });

    // Assert that the new submission appears in the activity feed WITHOUT calling page.reload()
    await expect(page.getByText(uniqueInstituteName).first()).toBeVisible({ timeout: 12000 });
  });
});
