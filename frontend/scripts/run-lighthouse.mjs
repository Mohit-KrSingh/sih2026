#!/usr/bin/env node
import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "..");

// Auto-discover Playwright Chromium if CHROME_PATH is not set
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

const chromePath = getChromePath();
if (chromePath) {
  process.env.CHROME_PATH = chromePath;
}

const { default: lighthouse } = await import("lighthouse");
const chromeLauncher = await import("chrome-launcher");

const TARGET_PAGES = [
  { path: "/", name: "Public Homepage" },
  { path: "/activate", name: "Institution Activation" },
  { path: "/login/college", name: "College Login Portal" },
  { path: "/verify", name: "Credential Verification" },
  { path: "/student", name: "Student Consent Portal" },
];

const MINIMUM_SCORE = 95;
const baseUrl = process.env.BASE_URL || "http://localhost:5173";

console.log("=== EduTrace UX4G Lighthouse Accessibility Audit ===");
console.log(`Base URL: ${baseUrl}`);
console.log(`Target Threshold: ${MINIMUM_SCORE}/100\n`);

let chrome;
try {
  chrome = await chromeLauncher.launch({
    chromeFlags: ["--headless=new", "--no-sandbox", "--disable-gpu"],
  });

  const results = [];
  let allPassed = true;

  for (const page of TARGET_PAGES) {
    const fullUrl = `${baseUrl}${page.path}`;
    process.stdout.write(`Auditing ${page.name} (${page.path})... `);

    const report = await lighthouse(fullUrl, {
      port: chrome.port,
      onlyCategories: ["accessibility"],
      logLevel: "error",
      output: "json",
    });

    const rawScore = report.lhr.categories.accessibility.score;
    const score = Math.round(rawScore * 100);
    const passed = score >= MINIMUM_SCORE;

    if (!passed) allPassed = false;

    console.log(`${score}/100 [${passed ? "PASS" : "FAIL"}]`);

    results.push({
      page: page.name,
      path: page.path,
      score,
      status: passed ? "PASS" : "FAIL",
    });
  }

  console.log("\n--- Lighthouse Audit Summary ---");
  console.table(results);

  if (!allPassed) {
    console.error(`\nAudit failed: One or more pages scored below ${MINIMUM_SCORE}!`);
    process.exit(1);
  }

  console.log(`\nAll ${TARGET_PAGES.length} key pages exceeded the ${MINIMUM_SCORE}/100 accessibility threshold!`);
  process.exit(0);
} catch (err) {
  console.error("Lighthouse execution error:", err);
  process.exit(1);
} finally {
  if (chrome) {
    await chrome.kill();
  }
}
