import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";

test.describe("R15: Lighthouse Accessibility Audit (Threshold >= 95)", () => {
  // 5 key public & entry pages specified in task requirements
  const TARGET_PAGES = [
    { path: "/", name: "Public Homepage", minScore: 95 },
    { path: "/activate", name: "Institution Activation", minScore: 95 },
    { path: "/login/college", name: "College Login Portal", minScore: 95 },
    { path: "/verify", name: "Credential Verification", minScore: 95 },
    { path: "/student", name: "Student Consent Portal", minScore: 95 },
  ];

  function getChromePath() {
    if (process.env.CHROME_PATH && fs.existsSync(process.env.CHROME_PATH)) {
      return process.env.CHROME_PATH;
    }
    const localAppData = process.env.LOCALAPPDATA || "";
    const pwDir = path.join(localAppData, "ms-playwright");
    if (fs.existsSync(pwDir)) {
      const entries = fs.readdirSync(pwDir);
      for (const entry of entries) {
        if (entry.startsWith("chromium-")) {
          const candidate = path.join(pwDir, entry, "chrome-win64", "chrome.exe");
          if (fs.existsSync(candidate)) {
            return candidate;
          }
        }
      }
    }
    return undefined;
  }

  let chromeLauncher: any;
  let lighthouse: any;
  let chromeInstance: any;

  test.beforeAll(async () => {
    const cp = getChromePath();
    if (cp) {
      process.env.CHROME_PATH = cp;
    }
    chromeLauncher = await import("chrome-launcher");
    const lhModule = await import("lighthouse");
    lighthouse = lhModule.default;

    chromeInstance = await chromeLauncher.launch({
      chromeFlags: ["--headless=new", "--no-sandbox", "--disable-gpu"],
    });
  });

  test.afterAll(async () => {
    if (chromeInstance) {
      await chromeInstance.kill();
    }
  });

  for (const pageItem of TARGET_PAGES) {
    test(`Lighthouse accessibility score for ${pageItem.name} (${pageItem.path}) meets or exceeds ${pageItem.minScore}`, async () => {
      const fullUrl = `http://localhost:5173${pageItem.path}`;

      const report = await lighthouse(fullUrl, {
        port: chromeInstance.port,
        onlyCategories: ["accessibility"],
        logLevel: "error",
        output: "json",
      });

      const score = Math.round(report.lhr.categories.accessibility.score * 100);
      expect(score).toBeGreaterThanOrEqual(pageItem.minScore);
    });
  }
});
