import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

describe("UX4G and EduTrace Tokens", () => {
  it("configures Noto Sans as base font family in index.css and tailwind config", () => {
    const indexCss = fs.readFileSync(path.resolve(__dirname, "../index.css"), "utf8");
    expect(indexCss).toContain('font-family: var(--ux4g-font-family-base, "Noto Sans", system-ui, sans-serif)');

    const tailwindConfig = fs.readFileSync(path.resolve(__dirname, "../../tailwind.config.js"), "utf8");
    expect(tailwindConfig).toContain("Noto Sans");
  });

  it("sets light theme data-theme attribute on root html file", () => {
    const indexHtml = fs.readFileSync(path.resolve(__dirname, "../../index.html"), "utf8");
    expect(indexHtml).toContain('data-theme="light"');
  });

  it("provides EduTrace tokens file with zero raw hex colors", () => {
    const tokensCss = fs.readFileSync(path.resolve(__dirname, "../styles/tokens.css"), "utf8");
    expect(tokensCss).toContain("--edutrace-brand-primary");
    expect(tokensCss).toContain("--edutrace-flag-error-bg");
    expect(tokensCss).toContain("--edutrace-flag-exception-bg");
    expect(tokensCss).toContain("--edutrace-flag-warning-bg");
    expect(tokensCss).toContain("--edutrace-flag-info-bg");
    // Strictly no raw hex
    expect(tokensCss).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});
