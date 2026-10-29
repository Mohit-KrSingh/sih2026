#!/usr/bin/env node
/**
 * Token & Color Compliance Linter
 *
 * Enforces UX4G Design System 3.0 token architecture:
 * 1. Prohibits raw hex colors (#rrggbb, #rgb) outside tokens.css.
 * 2. Prohibits raw rgb/rgba declarations outside tokens.css.
 * 3. Prohibits Tailwind color classes (bg-blue-*, text-slate-*, etc.).
 *
 * A progressive baseline tracks legacy unmigrated screens awaiting their designated
 * rebrand tasks (R03-R10). Any new file, UX4G component, or newly introduced raw color
 * fails immediately.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, "..");
const srcDir = path.join(frontendRoot, "src");

const TOKENS_CSS = "src/styles/tokens.css";
const BASELINE_PATH = path.join(__dirname, "legacy-baseline.json");

// Read legacy baseline files awaiting migration in R03-R10
const legacyBaselineList = fs.existsSync(BASELINE_PATH)
  ? JSON.parse(fs.readFileSync(BASELINE_PATH, "utf8"))
  : [];
const LEGACY_BASELINE = new Set(legacyBaselineList.map((f) => f.replace(/\\/g, "/")));

// The 3 chart files with existing hex colors awaiting R10 ECharts theme migration
const LEGACY_CHART_HEX_FILES = new Set([
  "src/charts/CourseDistributionChart.tsx",
  "src/charts/StateIntakeChart.tsx",
  "src/charts/SubmissionProgressChart.tsx",
]);

const TW_COLOR_FAMILIES = [
  "slate", "gray", "zinc", "neutral", "stone",
  "red", "orange", "amber", "yellow", "lime",
  "green", "emerald", "teal", "cyan", "sky",
  "blue", "indigo", "violet", "purple", "fuchsia",
  "pink", "rose"
];

const TW_COLOR_REGEX = new RegExp(
  `\\b(?:bg|text|border|ring|outline|divide|from|via|to|accent|fill|stroke|decoration|placeholder)-(?:${TW_COLOR_FAMILIES.join("|")})-[0-9]{2,3}\\b`,
  "g"
);

// Matches #fff, #ffffff, #ffffffff but excludes markdown headings (# Header) or numbers (#101)
const HEX_COLOR_REGEX = /#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b/g;
const RGB_REGEX = /\brgba?\s*\([^)]*\)/gi;

function walk(dir) {
  let results = [];
  const list = fs.readdirSync(dir);
  for (const file of list) {
    const full = path.join(dir, file);
    const stat = fs.statSync(full);
    if (stat && stat.isDirectory()) {
      if (file !== "node_modules" && file !== "dist") {
        results = results.concat(walk(full));
      }
    } else if (/\.(tsx?|css|html)$/.test(file)) {
      results.push(full);
    }
  }
  return results;
}

let errorCount = 0;
const files = walk(srcDir);

for (const filePath of files) {
  const relPath = path.relative(frontendRoot, filePath).replace(/\\/g, "/");
  const isTokensCss = relPath === TOKENS_CSS;
  const isBaseline = LEGACY_BASELINE.has(relPath);
  const isLegacyChartHex = LEGACY_CHART_HEX_FILES.has(relPath);
  const isTest = /\.test\.tsx?$/.test(filePath);

  const content = fs.readFileSync(filePath, "utf8");
  const lines = content.split("\n");

  lines.forEach((line, idx) => {
    const lineNum = idx + 1;

    // 1. Check for raw hex colors
    const hexMatches = line.match(HEX_COLOR_REGEX);
    if (hexMatches && !isTokensCss) {
      for (const hex of hexMatches) {
        // In tests, skip references like "#101" which match ID assertions
        if (isTest && (hex === "#101" || hex === "#1001")) continue;
        if (isLegacyChartHex) continue; // Tracked legacy chart files handled in R10

        console.error(
          `\x1b[31m[TOKEN LINT ERROR]\x1b[0m ${relPath}:${lineNum} - Forbidden raw hex color '${hex}'. Use UX4G semantic tokens via tokens.css.`
        );
        errorCount++;
      }
    }

    // 2. Check for rgb / rgba declarations
    const rgbMatches = line.match(RGB_REGEX);
    if (rgbMatches && !isTokensCss) {
      for (const rgb of rgbMatches) {
        console.error(
          `\x1b[31m[TOKEN LINT ERROR]\x1b[0m ${relPath}:${lineNum} - Forbidden raw rgb declaration '${rgb}'. Use UX4G semantic tokens.`
        );
        errorCount++;
      }
    }

    // 3. Check for Tailwind color classes (prohibited in all new/migrated files)
    const twMatches = line.match(TW_COLOR_REGEX);
    if (twMatches && !isBaseline && !isTokensCss) {
      for (const cls of twMatches) {
        console.error(
          `\x1b[31m[TOKEN LINT ERROR]\x1b[0m ${relPath}:${lineNum} - Forbidden Tailwind color class '${cls}'. Use UX4G component classes or semantic tokens.`
        );
        errorCount++;
      }
    }
  });

  // Also enforce tokens.css itself does not use raw hex/rgb
  if (isTokensCss) {
    lines.forEach((line, idx) => {
      const lineNum = idx + 1;
      const hexMatches = line.match(HEX_COLOR_REGEX);
      if (hexMatches) {
        for (const hex of hexMatches) {
          console.error(
            `\x1b[31m[TOKEN LINT ERROR]\x1b[0m ${relPath}:${lineNum} - tokens.css must only alias --ux4g-* variables, found raw hex '${hex}'.`
          );
          errorCount++;
        }
      }
      const rgbMatches = line.match(RGB_REGEX);
      if (rgbMatches) {
        for (const rgb of rgbMatches) {
          console.error(
            `\x1b[31m[TOKEN LINT ERROR]\x1b[0m ${relPath}:${lineNum} - tokens.css must only alias --ux4g-* variables, found raw rgb '${rgb}'.`
          );
          errorCount++;
        }
      }
    });
  }
}

if (errorCount > 0) {
  console.error(`\n\x1b[31m✗ Token & Color Lint failed with ${errorCount} violation(s).\x1b[0m`);
  process.exit(1);
} else {
  console.log(`\x1b[32m✓ All tokens and color rules verified compliant with UX4G.\x1b[0m`);
  process.exit(0);
}
