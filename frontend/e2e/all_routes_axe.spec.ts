import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { execSync } from "child_process";
import path from "path";

// Routes defined in SPEC §19
const PUBLIC_ROUTES = [
  "/",
  "/activate",
  "/login/college",
  "/login/aicte",
  "/verify",
  "/student",
  "/help",
];

const COLLEGE_ROUTES = [
  "/college/dashboard",
  "/college/seats",
  "/college/students",
  "/college/students/new",
  "/college/upload",
  "/college/validation",
  "/college/submit",
  "/college/queries",
  "/college/change-requests",
  "/college/staff",
  "/college/api-keys",
];

const AICTE_ROUTES = [
  "/aicte/overview",
  "/aicte/approvals",
  "/aicte/intake",
  "/aicte/compliance",
  "/aicte/duplicates",
  "/aicte/anomalies",
  "/aicte/review",
  "/aicte/explore",
  "/aicte/reports",
  "/aicte/audit",
  "/aicte/verifiers",
  "/aicte/rules",
];

const VERIFIER_ROUTES = [
  "/verifier/search",
  "/verifier/history",
];

test.describe("R15: Axe-Core Accessibility Audit Across All SPEC §19 Routes", () => {
  const collegeEmail = "admin@mmit-mumbai.ac.in";
  const collegePassword = "Demo@12345";

  const aicteEmail = "aicte_admin@aicte-india.org";
  const aictePassword = "Demo@12345";

  const verifierEmail = "verifier@tcs-verifications.com";
  const verifierPassword = "Demo@12345";

  test.beforeEach(async () => {
    try {
      const rootDir = process.cwd().endsWith("frontend") ? path.resolve(process.cwd(), "..") : process.cwd();
      const resetCmd = `"${path.join(rootDir, ".venv/Scripts/python.exe")}" -c "import sys; sys.path.insert(0, 'backend'); from app.db import get_redis; r = next(get_redis()); keys = r.keys('ratelimit:*'); (r.delete(*keys) if keys else None)"`;
      execSync(resetCmd, { cwd: rootDir });
    } catch (e) {
      console.warn("Rate limit reset warning:", e);
    }
  });

  // 1. Scan Public Routes
  for (const route of PUBLIC_ROUTES) {
    test(`axe-core scan on public route: ${route}`, async ({ page }) => {
      await page.goto(route);
      await page.waitForLoadState("domcontentloaded");

      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();

      const severeViolations = results.violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious"
      );

      if (severeViolations.length > 0) {
        console.error(`Axe violations on ${route}:`, JSON.stringify(severeViolations, null, 2));
      }

      expect(severeViolations).toEqual([]);
    });
  }

  // 2. Scan College Routes
  test.describe("College Protected Routes", () => {
    test.beforeEach(async ({ page }) => {
      await page.goto("/login/college");
      await page.getByLabel("Official Institutional Email").fill(collegeEmail);
      await page.getByLabel("Password").fill(collegePassword);
      await page.getByRole("button", { name: "Sign in as college" }).click();

      const mfaInput = page.getByLabel("Authenticator Code");
      if (await mfaInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await mfaInput.fill("123456");
        await page.getByRole("button", { name: /Verify and sign in|Verify code|Verify MFA/i }).click();
      }

      await page.waitForURL("**/college/dashboard", { timeout: 15000 });
    });

    for (const route of COLLEGE_ROUTES) {
      test(`axe-core scan on college route: ${route}`, async ({ page }) => {
        await page.goto(route);
        await page.waitForLoadState("domcontentloaded");
        await page.waitForTimeout(500);

        const results = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
          .analyze();

        const severeViolations = results.violations.filter(
          (v) => v.impact === "critical" || v.impact === "serious"
        );

        if (severeViolations.length > 0) {
          console.error(`Axe violations on ${route}:`, JSON.stringify(severeViolations, null, 2));
        }

        expect(severeViolations).toEqual([]);
      });
    }
  });

  // 3. Scan AICTE Protected Routes
  test.describe("AICTE Protected Routes", () => {
    test.beforeEach(async ({ page }) => {
      await page.goto("/login/aicte");
      await page.getByLabel("Official AICTE Email").fill(aicteEmail);
      await page.getByLabel("Password").fill(aictePassword);
      await page.getByRole("button", { name: "Sign in to AICTE portal" }).click();

      const mfaInput = page.getByLabel("Authenticator Code");
      if (await mfaInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await mfaInput.fill("123456");
        await page.getByRole("button", { name: /Verify and sign in|Verify code|Verify MFA/i }).click();
      }

      await page.waitForURL("**/aicte/**", { timeout: 15000 });
    });

    for (const route of AICTE_ROUTES) {
      test(`axe-core scan on AICTE route: ${route}`, async ({ page }) => {
        await page.goto(route);
        await page.waitForLoadState("domcontentloaded");
        await page.waitForTimeout(500);

        const results = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
          .analyze();

        const severeViolations = results.violations.filter(
          (v) => v.impact === "critical" || v.impact === "serious"
        );

        if (severeViolations.length > 0) {
          console.error(`Axe violations on ${route}:`, JSON.stringify(severeViolations, null, 2));
        }

        expect(severeViolations).toEqual([]);
      });
    }
  });

  // 4. Scan Verifier Protected Routes
  test.describe("Verifier Protected Routes", () => {
    test.beforeEach(async ({ page }) => {
      await page.goto("/login/college");
      await page.getByLabel("Official Institutional Email").fill(verifierEmail);
      await page.getByLabel("Password").fill(verifierPassword);
      await page.getByRole("button", { name: "Sign in as college" }).click();

      await page.waitForURL("**/verifier/search**", { timeout: 15000 });
    });

    for (const route of VERIFIER_ROUTES) {
      test(`axe-core scan on verifier route: ${route}`, async ({ page }) => {
        await page.goto(route);
        await page.waitForLoadState("domcontentloaded");
        await page.waitForTimeout(500);

        const results = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
          .analyze();

        const severeViolations = results.violations.filter(
          (v) => v.impact === "critical" || v.impact === "serious"
        );

        if (severeViolations.length > 0) {
          console.error(`Axe violations on ${route}:`, JSON.stringify(severeViolations, null, 2));
        }

        expect(severeViolations).toEqual([]);
      });
    }
  });
});
