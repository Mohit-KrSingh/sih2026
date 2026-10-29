import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.describe("UX4G Page Shell & Accessibility Verification (R04)", () => {
  test("runs axe-core on public page shell landmarks with 0 violations", async ({ page }) => {
    await page.goto("/");

    // Scan the core layout shell landmarks: header and footer
    const shellResults = await new AxeBuilder({ page })
      .include("header")
      .include("footer")
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    expect(shellResults.violations).toEqual([]);
  });

  test("runs axe-core on full public page with 0 critical or serious violations", async ({ page }) => {
    await page.goto("/");

    const pageResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    const criticalOrSerious = pageResults.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious"
    );

    expect(criticalOrSerious).toEqual([]);
  });

  test("skip link is first focusable element and jumps to main content", async ({ page }) => {
    await page.goto("/");

    // Tab 1 from clean page state lands on Skip Link
    await page.keyboard.press("Tab");
    const skipLink = page.getByRole("link", { name: "Skip to main content" });
    await expect(skipLink).toBeFocused();
    await expect(skipLink).toBeVisible();

    // Activating Skip Link moves focus directly to main content
    await page.keyboard.press("Enter");
    const mainEl = page.locator("main#main-content");
    await expect(mainEl).toBeFocused();
  });

  test("tabbing order follows: skip link, logo/utility, nav, content, footer", async ({ page }) => {
    await page.goto("/");

    // 1. Skip link
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();

    // 2. Utility bar: Accessibility button
    await page.keyboard.press("Tab");
    await expect(page.getByRole("button", { name: "Accessibility options" })).toBeFocused();

    // 3. Utility bar: Language switch button
    await page.keyboard.press("Tab");
    await expect(page.getByRole("button", { name: "English" })).toBeFocused();

    // 4. Utility bar: College Login link
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "College Login" }).first()).toBeFocused();

    // 5. Utility bar: AICTE Login link
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "AICTE Login" }).first()).toBeFocused();

    // 6. Header: EduTrace Home Brand Logo
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: /EduTrace.*Central Portal/i })).toBeFocused();

    // 7. Header Nav: Home Link
    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Home", exact: true })).toBeFocused();
  });

  test("verifies semantic landmarks header, nav, main, footer exist on page", async ({ page }) => {
    await page.goto("/");

    // Semantic landmark verification
    await expect(page.locator("header")).toBeVisible();
    await expect(page.locator("nav[aria-label='Main Navigation']")).toBeVisible();
    await expect(page.locator("main#main-content")).toBeVisible();
    await expect(page.locator("footer[role='contentinfo']")).toBeVisible();
  });

  test("footer displays mandatory demo disclaimer, grievance contact, and secondary links", async ({ page }) => {
    await page.goto("/");

    const footer = page.locator("footer[role='contentinfo']");
    await expect(footer).toBeVisible();

    // SPEC §2 Rule 10 mandatory demo mode disclaimer
    await expect(footer).toContainText(
      "Demo mode: APAAR registry is simulated. EduTrace is a prototype and not an official government service."
    );

    // Contacts
    await expect(footer).toContainText("grievance@edutrace.ac.in");
    await expect(footer).toContainText("support@edutrace.ac.in");

    // Prohibits "Powered by NeGD" per task description
    await expect(footer).not.toContainText("Powered by NeGD");

    // Secondary navigation links
    await expect(page.getByRole("link", { name: "Privacy Policy" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Terms of Service" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Accessibility Statement" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Help & Glossary" })).toBeVisible();
  });
});
