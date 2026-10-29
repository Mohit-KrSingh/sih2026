import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { execSync } from "child_process";
import path from "path";

test.describe("R08: Flags, Badges, and Alerts", () => {
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

    // Handle MFA if enabled for the account
    const mfaInput = page.getByLabel("Authenticator Code");
    if (await mfaInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await mfaInput.fill("123456");
      await page.getByRole("button", { name: /Verify and sign in|Verify code|Verify MFA/i }).click();
    }

    await page.waitForURL("**/college/dashboard", { timeout: 15000 });
  }

  test("renders all four FlagBadge levels with text labels and icons without relying on color alone", async ({
    page,
  }) => {
    await page.goto("/dev/components");
    await expect(page.locator("h1")).toContainText("UX4G Component Showcase");

    // 1. Error FlagBadge (red filled, cancel icon, Error label)
    const errorBadge = page.locator('[data-testid="flag-badge-error"]').first();
    await expect(errorBadge).toBeVisible();
    await expect(errorBadge).toHaveAttribute("role", "status");
    await expect(errorBadge).toContainText("Error");
    await expect(errorBadge.locator(".ux4g-icon")).toHaveText("cancel");

    // 2. Exception FlagBadge (red outlined, report_problem icon, Exception label)
    const exceptionBadge = page.locator('[data-testid="flag-badge-exception"]').first();
    await expect(exceptionBadge).toBeVisible();
    await expect(exceptionBadge).toHaveAttribute("role", "status");
    await expect(exceptionBadge).toContainText("Exception");
    await expect(exceptionBadge.locator(".ux4g-icon")).toHaveText("report_problem");

    // 3. Warning FlagBadge (orange, warning icon, Warning label)
    const warningBadge = page.locator('[data-testid="flag-badge-warning"]').first();
    await expect(warningBadge).toBeVisible();
    await expect(warningBadge).toHaveAttribute("role", "status");
    await expect(warningBadge).toContainText("Warning");
    await expect(warningBadge.locator(".ux4g-icon")).toHaveText("warning");

    // 4. Info FlagBadge (neutral grey, info icon, Info label)
    const infoBadge = page.locator('[data-testid="flag-badge-info"]').first();
    await expect(infoBadge).toBeVisible();
    await expect(infoBadge).toHaveAttribute("role", "status");
    await expect(infoBadge).toContainText("Info");
    await expect(infoBadge.locator(".ux4g-icon")).toHaveText("info");

    // 5. Axe-core accessibility scan on badge showcase section
    const badgeResults = await new AxeBuilder({ page })
      .include('[data-testid="showcase-flag-badges"]')
      .analyze();
    expect(badgeResults.violations).toEqual([]);
  });

  test("renders specialized alerts for submit gate, locked data, suspended approval, and demo mode", async ({
    page,
  }) => {
    await page.goto("/dev/components");

    // 1. Submit Gate Alert (Passed and Blocked)
    const submitGateAlerts = page.locator('[data-testid="submit-gate-alert"]');
    await expect(submitGateAlerts.first()).toBeVisible();
    await expect(submitGateAlerts.first()).toHaveClass(/ux4g-alert-success/);
    await expect(submitGateAlerts.nth(1)).toHaveClass(/ux4g-alert-error/);
    await expect(submitGateAlerts.nth(1)).toContainText("Submit Gate Blocked");

    // 2. Locked Data Alert
    const lockedAlert = page.locator('[data-testid="locked-data-alert"]');
    await expect(lockedAlert).toBeVisible();
    await expect(lockedAlert).toHaveClass(/ux4g-alert-info/);
    await expect(lockedAlert).toContainText("Central Repository Locked");

    // 3. Suspended Approval Alert (Read-only banner)
    const suspendedAlert = page.locator('[data-testid="suspended-approval-alert"]');
    await expect(suspendedAlert).toBeVisible();
    await expect(suspendedAlert).toHaveClass(/ux4g-alert-error/);
    await expect(suspendedAlert).toContainText("AICTE Approval Suspended");
    await expect(suspendedAlert).toContainText("HTTP 403");

    // 4. Demo Mode Alert
    const demoAlert = page.locator('[data-testid="demo-mode-alert"]');
    await expect(demoAlert).toBeVisible();
    await expect(demoAlert).toHaveClass(/ux4g-alert-info/);
    await expect(demoAlert).toContainText("Demonstration Environment");

    // 5. Axe-core accessibility scan on alerts showcase section
    const alertResults = await new AxeBuilder({ page })
      .include('[data-testid="showcase-alerts"]')
      .analyze();
    expect(alertResults.violations).toEqual([]);
  });

  test("renders submit gate and locked data UX4G alerts in college submission journey", async ({
    page,
  }) => {
    await loginAsCollege(page);

    await page.goto("/college/submit");
    await expect(page.locator("h1")).toContainText("Final Data Submission");

    // Gate banner or locked data banner uses UX4G Alert
    const complianceAlert = page
      .locator('[data-testid="locked-data-alert"], [data-testid="submit-gate-alert"]')
      .first();
    await expect(complianceAlert).toBeVisible();
    await expect(complianceAlert).toHaveClass(/ux4g-alert/);

    // Run axe scan on submit page
    const axeResults = await new AxeBuilder({ page })
      .disableRules(["color-contrast"]) // contrast verified in dedicated unit test suite
      .analyze();
    expect(axeResults.violations).toEqual([]);
  });
});
