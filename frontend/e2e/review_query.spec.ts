import { test, expect } from "@playwright/test";
import { execSync } from "child_process";
import path from "path";

test.describe("T25: AICTE Review Queue and College Query Round-Trip End-to-End", () => {
  const officerEmail = "aicte_officer@aicte-india.org";
  const collegeEmail = "admin@mmit-mumbai.ac.in";
  const password = "Demo@12345";
  const queryMessage = "Please provide certified justification copy for the additional 8 intake seats.";
  const collegeResponse =
    "High Court interim bench order attached confirming sanction of 8 seats under supernumerary quota.";
  const acceptNote = "Clarification verified against court records and accepted.";

  test.beforeEach(async () => {
    try {
      const rootDir = path.resolve(process.cwd(), "..");
      const resetCmd = `"${path.join(rootDir, ".venv/Scripts/python.exe")}" -c "import sys; sys.path.insert(0, 'backend'); from app.db import get_redis; r = next(get_redis()); keys = r.keys('ratelimit:*'); (r.delete(*keys) if keys else None)"`;
      execSync(resetCmd, { cwd: rootDir });
    } catch (e) {
      console.warn("Rate limit reset warning:", e);
    }
  });

  test("completes the full review query round trip: raise query -> college responds -> officer accepts", async ({
    page,
  }) => {
    // -------------------------------------------------------------------------
    // Step 1: AICTE Officer signs in and navigates to Review Queue
    // -------------------------------------------------------------------------
    await page.goto("/login/aicte");
    await expect(page.locator("h1")).toContainText("AICTE Central Portal");

    await page.getByLabel("Official AICTE Email").fill(officerEmail);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in to AICTE portal" }).click();

    // Verify redirected to dashboard / navigation visible
    await page.waitForURL("**/aicte/**", { timeout: 10000 });

    // Navigate to Review Queue
    await page.goto("/aicte/review");
    await expect(page.locator("h1")).toContainText("AICTE Submission Review Queue");

    // Wait for review queue table to load
    await expect(
      page.getByText("Mumbai Metropolitan Institute of Technology"),
    ).toBeVisible({ timeout: 10000 });

    // Open first review item (MMIT Mumbai)
    const mmitRow = page.locator("tr").filter({ hasText: "Mumbai Metropolitan Institute of Technology" });
    await mmitRow.getByRole("button", { name: "Review Item" }).click();

    // Verify Inspection Modal opens
    await expect(page.getByText("Take Review Action")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("INTAKE_EXCEEDED").first()).toBeVisible();

    // -------------------------------------------------------------------------
    // Step 2: Officer selects "Raise Clarification Query", types inquiry, dispatches
    // -------------------------------------------------------------------------
    await page.getByLabel("Raise Clarification Query").click();

    const noteField = page.getByPlaceholder(/Please provide a legible certified copy/i);
    await noteField.fill(queryMessage);

    const dispatchBtn = page.getByRole("button", { name: "Dispatch Query to College" });
    await dispatchBtn.click();

    // Verify success banner appears
    await expect(
      page.getByText("Clarification query successfully dispatched to institution."),
    ).toBeVisible({ timeout: 10000 });

    // Close modal
    await page.getByRole("button", { name: "Close", exact: true }).click();

    // Sign out officer via navbar
    const signOutBtn = page.getByRole("button", { name: /Sign out/i });
    if (await signOutBtn.isVisible()) {
      await signOutBtn.click();
    } else {
      // Clear storage
      await page.evaluate(() => localStorage.clear());
    }

    // -------------------------------------------------------------------------
    // Step 3: College Admin signs in and views queries
    // -------------------------------------------------------------------------
    await page.goto("/login/college");
    await expect(page.locator("h1")).toContainText("College Portal Login");

    await page.getByLabel("Official Institutional Email").fill(collegeEmail);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in as college" }).click();

    await page.waitForURL("**/college/**", { timeout: 10000 });

    // Navigate to College Queries
    await page.goto("/college/queries");
    await expect(page.locator("h1")).toContainText("AICTE Clarification Queries");

    // Verify the inquiry from AICTE appears
    await expect(page.getByText(queryMessage).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Pending Your Response").first()).toBeVisible();

    // -------------------------------------------------------------------------
    // Step 4: College responds to inquiry
    // -------------------------------------------------------------------------
    const respondBtn = page.getByRole("button", { name: "Respond to Inquiry" });
    await expect(respondBtn.first()).toBeVisible();
    await respondBtn.first().click();

    await expect(
      page.getByText("Submit Official College Clarification"),
    ).toBeVisible();

    const clarificationTextarea = page.getByPlaceholder(/Provide clear legal, statutory/i);
    await clarificationTextarea.fill(collegeResponse);

    const submitResponseBtn = page.getByRole("button", {
      name: "Submit Response to AICTE",
    });
    await submitResponseBtn.click();

    // Verify success banner
    await expect(
      page.getByText("Clarification successfully submitted. Submission returned to Under Review."),
    ).toBeVisible({ timeout: 10000 });

    // Sign out college admin
    const collegeSignOut = page.getByRole("button", { name: /Sign out/i });
    if (await collegeSignOut.isVisible()) {
      await collegeSignOut.click();
    } else {
      await page.evaluate(() => localStorage.clear());
    }

    // -------------------------------------------------------------------------
    // Step 5: AICTE Officer signs in again to review answer and accept
    // -------------------------------------------------------------------------
    await page.goto("/login/aicte");
    await page.getByLabel("Official AICTE Email").fill(officerEmail);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in to AICTE portal" }).click();

    await page.waitForURL("**/aicte/**", { timeout: 10000 });
    await page.goto("/aicte/review");
    await expect(page.locator("h1")).toContainText("AICTE Submission Review Queue");

    // Open item for MMIT Mumbai
    const mmitRowAgain = page.locator("tr").filter({ hasText: "Mumbai Metropolitan Institute of Technology" });
    await mmitRowAgain.getByRole("button", { name: "Review Item" }).click();

    // Verify clarification response visible in thread
    await expect(page.getByText(collegeResponse).first()).toBeVisible({ timeout: 10000 });

    // Select Accept Exception
    await page.getByLabel("Accept Exception").click();

    const acceptNoteField = page.getByPlaceholder(/Verified court order/i);
    await acceptNoteField.fill(acceptNote);

    const acceptBtn = page.getByRole("button", { name: "Accept & Resolve Exceptions" });
    await acceptBtn.click();

    // Verify accepted message
    await expect(
      page.getByText("Exceptions successfully accepted and resolved."),
    ).toBeVisible({ timeout: 10000 });

    // Close modal
    await page.getByRole("button", { name: "Close", exact: true }).click();

    // Item should now show Accepted badge in table
    await expect(page.getByText("Accepted").first()).toBeVisible({ timeout: 5000 });
  });
});
