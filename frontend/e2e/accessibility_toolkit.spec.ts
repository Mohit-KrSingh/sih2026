import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import path from "node:path";

test.describe("UX4G Accessibility Toolkit & Focus Verification (R05)", () => {
  test.beforeEach(async ({ page }) => {
    // Clear localStorage before each test run
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  });

  test("opens and closes accessibility toolkit dialog via utility bar trigger", async ({ page }) => {
    await page.goto("/");

    const trigger = page.locator("#a11y-trigger-btn");
    await expect(trigger).toBeVisible();
    await expect(trigger).toHaveAttribute("aria-expanded", "false");

    // Open panel
    await trigger.click();
    await expect(trigger).toHaveAttribute("aria-expanded", "true");

    const dialog = page.locator("div[role='dialog'][aria-modal='true']");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("heading", { name: "Accessibility Tools" })).toBeVisible();

    // Close via Close button
    const closeBtn = dialog.getByRole("button", { name: "Close accessibility tools" });
    await closeBtn.click();
    await expect(dialog).not.toBeVisible();
    await expect(trigger).toHaveAttribute("aria-expanded", "false");

    // Reopen and close via Escape key
    await trigger.click();
    await expect(dialog).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
  });

  test("toggles all five accessibility options and asserts DOM attributes and usability", async ({ page }) => {
    await page.goto("/");

    // Open panel
    await page.locator("#a11y-trigger-btn").click();
    const dialog = page.locator("div[role='dialog']");

    // 1. Text Sizing (3 steps: normal -> large -> x-large)
    const largeBtn = dialog.getByRole("button", { name: /Large \(112%\)/i });
    await largeBtn.click();
    await expect(page.locator("html")).toHaveAttribute("data-text-size", "large");

    const xlargeBtn = dialog.getByRole("button", { name: /X-Large \(125%\)/i });
    await xlargeBtn.click();
    await expect(page.locator("html")).toHaveAttribute("data-text-size", "x-large");

    const normalBtn = dialog.getByRole("button", { name: /Normal \(100%\)/i });
    await normalBtn.click();
    await expect(page.locator("html")).toHaveAttribute("data-text-size", "normal");

    // 2. Color Theme (Light / Dark)
    const darkBtn = dialog.getByRole("button", { name: "Dark" });
    await darkBtn.click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

    const lightBtn = dialog.getByRole("button", { name: "Light" });
    await lightBtn.click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");

    // 3. High Contrast
    const contrastSwitch = dialog.getByRole("switch", { name: /high contrast/i });
    await contrastSwitch.click();
    await expect(page.locator("html")).toHaveAttribute("data-contrast", "high");

    // 4. Underline Links
    const underlineSwitch = dialog.getByRole("switch", { name: /underline links/i });
    await underlineSwitch.click();
    await expect(page.locator("html")).toHaveAttribute("data-underline-links", "true");

    // 5. Reduce Motion
    const motionSwitch = dialog.getByRole("switch", { name: /reduce motion/i });
    await motionSwitch.click();
    await expect(page.locator("html")).toHaveAttribute("data-reduced-motion", "true");

    // Check page remains functional and interactive
    await dialog.getByRole("button", { name: "Done" }).click();
    await expect(dialog).not.toBeVisible();

    // Verify links and buttons still work on home page
    const collegeLogin = page.getByRole("link", { name: "College Login" }).first();
    await expect(collegeLogin).toBeVisible();
  });

  test("persists customized accessibility settings across page reload", async ({ page }) => {
    await page.goto("/");

    // Open panel and set multiple options
    await page.locator("#a11y-trigger-btn").click();
    const dialog = page.locator("div[role='dialog']");

    await dialog.getByRole("button", { name: /Large \(112%\)/i }).click();
    await dialog.getByRole("button", { name: "Dark" }).click();
    await dialog.getByRole("switch", { name: /high contrast/i }).click();
    await dialog.getByRole("switch", { name: /underline links/i }).click();
    await dialog.getByRole("button", { name: "Done" }).click();

    // Reload page
    await page.reload();

    // Assert persisted attributes
    await expect(page.locator("html")).toHaveAttribute("data-text-size", "large");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await expect(page.locator("html")).toHaveAttribute("data-contrast", "high");
    await expect(page.locator("html")).toHaveAttribute("data-underline-links", "true");
  });

  test("reset defaults button restores initial settings", async ({ page }) => {
    await page.goto("/");

    await page.locator("#a11y-trigger-btn").click();
    const dialog = page.locator("div[role='dialog']");

    // Customize
    await dialog.getByRole("button", { name: /X-Large \(125%\)/i }).click();
    await dialog.getByRole("switch", { name: /high contrast/i }).click();

    await expect(page.locator("html")).toHaveAttribute("data-text-size", "x-large");
    await expect(page.locator("html")).toHaveAttribute("data-contrast", "high");

    // Reset Defaults
    const resetBtn = dialog.getByRole("button", { name: /Reset Defaults/i });
    await resetBtn.click();

    await expect(page.locator("html")).toHaveAttribute("data-text-size", "normal");
    await expect(page.locator("html")).toHaveAttribute("data-contrast", "normal");
  });

  test("focus ring is visible on interactive elements and captured in screenshot test", async ({ page }) => {
    await page.goto("/");

    // Tab to Skip Link
    await page.keyboard.press("Tab");
    const skipLink = page.getByRole("link", { name: "Skip to main content" });
    await expect(skipLink).toBeFocused();

    // Tab to accessibility button
    await page.keyboard.press("Tab");
    const a11yTrigger = page.locator("#a11y-trigger-btn");
    await expect(a11yTrigger).toBeFocused();

    // Evaluate focus outline styles
    const outlineStyles = await a11yTrigger.evaluate((el) => {
      const computed = window.getComputedStyle(el);
      return {
        outlineStyle: computed.outlineStyle,
        outlineWidth: computed.outlineWidth,
      };
    });

    // Outline must be defined and visible
    expect(outlineStyles.outlineStyle).not.toBe("none");
    expect(parseFloat(outlineStyles.outlineWidth)).toBeGreaterThanOrEqual(1);

    // Save screenshot test verifying visible focus ring
    const screenshotDir = path.resolve(process.cwd(), "..", "docs", "screens");
    await a11yTrigger.screenshot({
      path: path.join(screenshotDir, "focus-ring-trigger.png"),
    });

    // Capture full page with focused element for visual proof
    await page.screenshot({
      path: path.join(screenshotDir, "focus-ring-page.png"),
    });
  });

  test("runs axe-core on open accessibility dialog with zero violations", async ({ page }) => {
    await page.goto("/");

    await page.locator("#a11y-trigger-btn").click();
    const dialog = page.locator("div[role='dialog']");
    await expect(dialog).toBeVisible();

    const results = await new AxeBuilder({ page })
      .include("div[role='dialog']")
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();

    expect(results.violations).toEqual([]);
  });
});
