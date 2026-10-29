import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const PUBLIC_ROUTES = [
  { path: "/", name: "Home Page" },
  { path: "/activate", name: "Institution Activation" },
  { path: "/login/college", name: "College Login" },
  { path: "/login/aicte", name: "AICTE Central Login" },
  { path: "/verify", name: "Credential Verification" },
  { path: "/student", name: "Student Consent Portal" },
];

test.describe("R06: Public Pages - Accessibility, Keyboard Navigation & Responsive Layout", () => {
  // 1. Accessibility Scan (axe-core)
  for (const route of PUBLIC_ROUTES) {
    test(`axe-core scan on ${route.path} reports zero critical or serious violations`, async ({ page }) => {
      await page.goto(route.path);
      await page.waitForLoadState("domcontentloaded");

      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();

      const severeViolations = results.violations.filter(
        (v) => v.impact === "critical" || v.impact === "serious"
      );

      expect(severeViolations).toEqual([]);
    });
  }

  // 2. Responsive 360px viewport check (no horizontal scrollbar)
  for (const route of PUBLIC_ROUTES) {
    test(`fits 360px wide phone without horizontal overflow: ${route.path}`, async ({ page }) => {
      await page.setViewportSize({ width: 360, height: 800 });
      await page.goto(route.path);
      await page.waitForLoadState("domcontentloaded");

      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
      });

      expect(hasHorizontalScroll).toBe(false);
    });
  }

  // 3. Keyboard navigation tests
  test("home page allows keyboard navigation through entry cards", async ({ page }) => {
    await page.goto("/");

    // Skip to main content
    await page.keyboard.press("Tab");
    await page.keyboard.press("Enter");

    // Tab through to the first entry card button
    const activateBtn = page.getByRole("button", { name: "Begin activation" });
    await activateBtn.focus();
    await expect(activateBtn).toBeFocused();

    // Tab to next entry card button
    await page.keyboard.press("Tab");
    const collegeLoginBtn = page.getByRole("button", { name: "Sign in as college" });
    await expect(collegeLoginBtn).toBeFocused();

    // Tab to AICTE login card button
    await page.keyboard.press("Tab");
    const aicteLoginBtn = page.getByRole("button", { name: "Sign in to AICTE" });
    await expect(aicteLoginBtn).toBeFocused();

    // Tab to Verify card button
    await page.keyboard.press("Tab");
    const verifyBtn = page.getByRole("button", { name: "Verify credential" });
    await expect(verifyBtn).toBeFocused();
  });

  test("activate page form is operable via keyboard", async ({ page }) => {
    await page.goto("/activate");

    const input = page.getByLabel("AICTE Institute Identifier");
    await input.focus();
    await expect(input).toBeFocused();

    await page.keyboard.type("1-10000004");
    await page.keyboard.press("Tab");

    const verifyBtn = page.getByRole("button", { name: "Verify institution" });
    await expect(verifyBtn).toBeFocused();
    await page.keyboard.press("Enter");

    await expect(page.getByText("Institution Verified in AICTE Master Directory")).toBeVisible({
      timeout: 10000,
    });
  });

  test("college login form is operable via keyboard", async ({ page }) => {
    await page.goto("/login/college");

    const emailInput = page.getByLabel("Official Institutional Email");
    await emailInput.focus();
    await expect(emailInput).toBeFocused();

    await page.keyboard.type("test@college.edu.in");
    await page.keyboard.press("Tab");

    const passwordInput = page.getByLabel("Password");
    await expect(passwordInput).toBeFocused();

    await page.keyboard.type("SecretPassword");
    await page.keyboard.press("Tab"); // Forgot password link
    await page.keyboard.press("Tab"); // Submit button

    const signInBtn = page.getByRole("button", { name: "Sign in as college" });
    await expect(signInBtn).toBeFocused();
  });

  test("verify page form is operable via keyboard and shows consent notice on APAAR ID", async ({
    page,
  }) => {
    await page.goto("/verify");

    const input = page.getByLabel("Verification Identifier (VID) or APAAR ID");
    await input.focus();
    await expect(input).toBeFocused();

    await page.keyboard.type("111122223333");
    await page.keyboard.press("Tab");

    const verifyBtn = page.getByRole("button", { name: "Verify credential" });
    await expect(verifyBtn).toBeFocused();
    await page.keyboard.press("Enter");

    await expect(page.getByText("DPDP Consent Protocol Required")).toBeVisible({ timeout: 10000 });
  });

  test("student portal allows keyboard interaction to initiate OTP flow", async ({ page }) => {
    await page.goto("/student");

    const input = page.getByLabel("APAAR Identification Number");
    await input.focus();
    await expect(input).toBeFocused();

    await page.keyboard.type("111122223333");
    await page.keyboard.press("Tab");

    const sendOtpBtn = page.getByRole("button", { name: "Send verification OTP" });
    await expect(sendOtpBtn).toBeFocused();
    await page.keyboard.press("Enter");

    await expect(page.getByText("Step 2: Enter Verification OTP")).toBeVisible({ timeout: 10000 });
  });
});
