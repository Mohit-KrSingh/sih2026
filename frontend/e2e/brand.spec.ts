import { test, expect } from "@playwright/test";

test.describe("Brand verification across public pages (R01)", () => {
  const publicPages = [
    { path: "/", name: "Home Page" },
    { path: "/activate", name: "Activate College" },
    { path: "/login/college", name: "College Login" },
    { path: "/login/aicte", name: "AICTE Login" },
    { path: "/verify", name: "Verify Record" },
    { path: "/student", name: "Student Portal" },
  ];

  for (const { path, name } of publicPages) {
    test(`asserts <title> and header on ${name} (${path}) contain EduTrace`, async ({ page }) => {
      await page.goto(path);

      // Check document title
      await expect(page).toHaveTitle(/EduTrace/);

      // Check header brand
      const header = page.locator("header");
      await expect(header).toBeVisible();
      await expect(header).toContainText("EduTrace");
    });
  }
});
