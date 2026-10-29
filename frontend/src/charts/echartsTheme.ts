import * as echarts from "echarts";

/**
 * UX4G Design System 3.0 ECharts Theme
 *
 * Defines the colour-blind safe visual palette and semantic chart tokens
 * derived strictly from UX4G Design System variables (--ux4g-* / --edutrace-chart-*).
 */

export const UX4G_CHART_THEME = "ux4g";

export interface ChartThemeTokens {
  primary: string;
  secondary: string;
  accent: string;
  success: string;
  blue: string;
  purple: string;
  error: string;
  neutral: string;
  textPrimary: string;
  textSecondary: string;
  axisLine: string;
  splitLine: string;
  palette: string[];
}

/**
 * Dynamically resolves chart colors from document root CSS variables.
 * Ensures strict parity with UX4G semantic light and dark themes.
 */
export function getChartThemeTokens(): ChartThemeTokens {
  const getProp = (name: string, fallback: string): string => {
    if (typeof window !== "undefined" && typeof document !== "undefined") {
      const val = window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      if (val) return val;
    }
    return fallback;
  };

  const primary = getProp("--edutrace-chart-primary", "var(--edutrace-chart-primary)");
  const secondary = getProp("--edutrace-chart-secondary", "var(--edutrace-chart-secondary)");
  const accent = getProp("--edutrace-chart-accent", "var(--edutrace-chart-accent)");
  const success = getProp("--edutrace-chart-success", "var(--edutrace-chart-success)");
  const blue = getProp("--edutrace-chart-blue", "var(--edutrace-chart-blue)");
  const purple = getProp("--edutrace-chart-purple", "var(--edutrace-chart-purple)");
  const error = getProp("--edutrace-chart-error", "var(--edutrace-chart-error)");
  const neutral = getProp("--edutrace-chart-neutral", "var(--edutrace-chart-neutral)");

  const textPrimary = getProp("--edutrace-chart-text-primary", "var(--edutrace-chart-text-primary)");
  const textSecondary = getProp("--edutrace-chart-text-secondary", "var(--edutrace-chart-text-secondary)");
  const axisLine = getProp("--edutrace-chart-axis-line", "var(--edutrace-chart-axis-line)");
  const splitLine = getProp("--edutrace-chart-split-line", "var(--edutrace-chart-split-line)");

  return {
    primary,
    secondary,
    accent,
    success,
    blue,
    purple,
    error,
    neutral,
    textPrimary,
    textSecondary,
    axisLine,
    splitLine,
    palette: [
      primary,
      secondary,
      accent,
      success,
      blue,
      purple,
      error,
      neutral,
    ],
  };
}

let themeRegistered = false;

/**
 * Register UX4G theme in Apache ECharts instance.
 */
export function registerUx4gTheme(): void {
  if (themeRegistered) return;
  const tokens = getChartThemeTokens();

  echarts.registerTheme(UX4G_CHART_THEME, {
    color: tokens.palette,
    textStyle: {
      fontFamily: "Noto Sans, system-ui, sans-serif",
      color: tokens.textPrimary,
    },
    title: {
      textStyle: {
        fontWeight: "bold",
        color: tokens.textPrimary,
      },
      subtextStyle: {
        color: tokens.textSecondary,
      },
    },
    line: {
      itemStyle: { borderWidth: 2 },
      lineStyle: { width: 3 },
      symbolSize: 8,
      symbol: "emptyCircle",
      smooth: false,
    },
    bar: {
      itemStyle: {
        barBorderWidth: 0,
        barBorderColor: "transparent",
      },
    },
    categoryAxis: {
      axisLine: { show: true, lineStyle: { color: tokens.axisLine } },
      axisTick: { show: true, lineStyle: { color: tokens.axisLine } },
      axisLabel: { color: tokens.textSecondary, fontSize: 11 },
      splitLine: { show: false },
    },
    valueAxis: {
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: tokens.textSecondary, fontSize: 11 },
      splitLine: { show: true, lineStyle: { color: tokens.splitLine, type: "dashed" } },
    },
    legend: {
      textStyle: { color: tokens.textSecondary, fontSize: 11 },
    },
    tooltip: {
      axisPointer: {
        lineStyle: { color: tokens.axisLine, width: 1 },
        crossStyle: { color: tokens.axisLine, width: 1 },
      },
    },
  });

  themeRegistered = true;
}
