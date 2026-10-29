import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import path from "path";

test.describe("T43: Real URLs, Navigation History, Tab Titles, and Protected Redirects", () => {
  const collegeEmail = "admin@mmit-mumbai.ac.in";
  const password = "Demo@12345";

  test.beforeEach(async () => {
    try {
      const rootDir = path.resolve(process.cwd(), "..");
      const resetCmd = `"${path.join(rootDir, ".venv/Scripts/python.exe")}" -c "import sys; sys.path.insert(0, 'backend'); from app.db import get_redis; r = next(get_redis()); keys = r.keys('ratelimit:*'); (r.delete(*keys) if keys else None)"`;
      execSync(resetCmd, { cwd: rootDir });
    } catch (e) {
      console.warn("Rate limit reset warning:", e);
    }
  });

  test("direct link to protected page redirects to login and returns back upon sign in", async ({
    page,
  }) => {
    // 1. Visit a protected page directly while logged out
    await page.goto("/college/validation");

    // 2. Expect redirect to college login
    await expect(page).toHaveURL(/\/login\/college/);
    await expect(page.locator("h1")).toContainText("College Portal Login");

    // 3. Log in with valid credentials
    await page.getByLabel("Official Institutional Email").fill(collegeEmail);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in as college" }).click();

    // 4. Expect to be returned directly to the requested protected page (/college/validation)
    await page.waitForURL("**/college/validation", { timeout: 10000 });
    await expect(page).toHaveURL(/\/college\/validation/);
    await expect(page.locator("h1")).toContainText("Validation Flags");

    // 5. Verify browser tab title was updated
    await expect(page).toHaveTitle(/Validation Flags \| EduTrace/);
  });

  test("browser back and forward move across at least 4 pages accurately", async ({
    page,
  }) => {
    // Sign in first
    await page.goto("/login/college");
    await page.getByLabel("Official Institutional Email").fill(collegeEmail);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in as college" }).click();
    await page.waitForURL("**/college/dashboard", { timeout: 10000 });

    // Page 1: Dashboard
    await expect(page).toHaveURL(/\/college\/dashboard/);
    await expect(page).toHaveTitle(/College Portal Dashboard \| EduTrace/);

    // Page 2: Seats & Intake
    await page.getByRole("link", { name: /Seats & Intake/i }).first().click();
    await page.waitForURL("**/college/seats");
    await expect(page).toHaveURL(/\/college\/seats/);
    await expect(page).toHaveTitle(/Seat Declarations & Intake Quotas \| EduTrace/);

    // Page 3: Students Directory
    await page.getByRole("link", { name: /^Students$/i }).first().click();
    await page.waitForURL("**/college/students");
    await expect(page).toHaveURL(/\/college\/students/);
    await expect(page).toHaveTitle(/Student Directory \| EduTrace/);

    // Page 4: Validation Flags
    await page.getByRole("link", { name: /Validation Flags/i }).first().click();
    await page.waitForURL("**/college/validation");
    await expect(page).toHaveURL(/\/college\/validation/);
    await expect(page).toHaveTitle(/Validation Flags \| EduTrace/);

    // --- Back navigation test (4 pages backwards) ---
    // Back 1: from Validation Flags -> Students Directory
    await page.goBack();
    await expect(page).toHaveURL(/\/college\/students/);
    await expect(page).toHaveTitle(/Student Directory \| EduTrace/);

    // Back 2: from Students Directory -> Seats & Intake
    await page.goBack();
    await expect(page).toHaveURL(/\/college\/seats/);
    await expect(page).toHaveTitle(/Seat Declarations & Intake Quotas \| EduTrace/);

    // Back 3: from Seats & Intake -> Dashboard
    await page.goBack();
    await expect(page).toHaveURL(/\/college\/dashboard/);
    await expect(page).toHaveTitle(/College Portal Dashboard \| EduTrace/);

    // --- Forward navigation test (4 pages forward) ---
    // Forward 1: Dashboard -> Seats
    await page.goForward();
    await expect(page).toHaveURL(/\/college\/seats/);

    // Forward 2: Seats -> Students
    await page.goForward();
    await expect(page).toHaveURL(/\/college\/students/);

    // Forward 3: Students -> Validation Flags
    await page.goForward();
    await expect(page).toHaveURL(/\/college\/validation/);
  });

  test("refreshing preserves current page URL and user authentication", async ({
    page,
  }) => {
    // Sign in and go to Seats
    await page.goto("/login/college");
    await page.getByLabel("Official Institutional Email").fill(collegeEmail);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in as college" }).click();
    await page.waitForURL("**/college/dashboard", { timeout: 10000 });

    await page.goto("/college/seats");
    await page.waitForURL("**/college/seats");
    await expect(page.locator("h1")).toContainText("Seat Declarations");

    // Reload the page
    await page.reload();

    // Verify still on /college/seats and still authenticated
    await expect(page).toHaveURL(/\/college\/seats/);
    await expect(page.locator("h1")).toContainText("Seat Declarations");
    await expect(page.getByText(collegeEmail).first()).toBeVisible();
    await expect(page).toHaveTitle(/Seat Declarations & Intake Quotas \| EduTrace/);
  });

  test("unknown URLs show not-found page with a link home", async ({ page }) => {
    await page.goto("/some-non-existent-page-url-404");
    await expect(page.locator("h1")).toContainText("Page Not Found");
    await expect(page.getByText("HTTP 404 Not Found")).toBeVisible();
    await expect(page).toHaveTitle(/404 Page Not Found \| EduTrace/);

    // Click Return to home button
    await page.getByRole("button", { name: "Return to home" }).click();
    await expect(page).toHaveURL("/");
  });
});
