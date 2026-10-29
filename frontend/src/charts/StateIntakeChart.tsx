import React from "react";
import ReactECharts from "echarts-for-react";
import type { StateMetricsItem } from "../types/analytics";
import { getChartThemeTokens, registerUx4gTheme, UX4G_CHART_THEME } from "./echartsTheme";
import { AccessibleChartCard } from "./AccessibleChartCard";

interface StateIntakeChartProps {
  data: StateMetricsItem[];
  height?: number;
  headerRight?: React.ReactNode;
}

export function StateIntakeChart({ data, height = 300, headerRight }: StateIntakeChartProps) {
  registerUx4gTheme();
  const tokens = getChartThemeTokens();

  const states = data.map((d) => d.state);
  const intake = data.map((d) => d.approved_intake);
  const enrolled = data.map((d) => d.total_enrolled);

  const totalIntake = intake.reduce((a, b) => a + b, 0);
  const totalEnrolled = enrolled.reduce((a, b) => a + b, 0);
  const overallUtilisation =
    totalIntake > 0 ? Math.round((totalEnrolled / totalIntake) * 100) : 0;

  const topState = [...data].sort((a, b) => b.approved_intake - a.approved_intake)[0];

  const summary = data.length > 0
    ? `Comparative analysis across ${data.length} states showing ${totalIntake.toLocaleString()} approved seats versus ${totalEnrolled.toLocaleString()} actual admissions (${overallUtilisation}% seat utilisation). ${topState ? `${topState.state} represents the largest capacity with ${topState.approved_intake.toLocaleString()} seats.` : ""}`
    : "No state metrics currently available.";

  const tableHeaders = ["State Jurisdiction", "Approved Intake", "Actual Enrolled", "Utilisation"];
  const tableRows = data.map((d) => [
    d.state,
    d.approved_intake,
    d.total_enrolled,
    `${d.approved_intake > 0 ? Math.round((d.total_enrolled / d.approved_intake) * 100) : 0}%`,
  ]);

  const option = {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "var(--edutrace-surface-page)",
      borderColor: tokens.axisLine,
      borderWidth: 1,
      textStyle: {
        color: tokens.textPrimary,
        fontSize: 12,
      },
      formatter: (params: any[]) => {
        const stateName = params[0]?.name || "";
        let res = `<div style="font-weight:600;margin-bottom:4px;color:${tokens.textPrimary}">${stateName}</div>`;
        params.forEach((p) => {
          res += `<div style="display:flex;justify-content:space-between;gap:12px;font-size:12px;">
            <span style="color:${tokens.textSecondary}">
              <span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${p.color};margin-right:6px;"></span>
              ${p.seriesName}
            </span>
            <span style="font-weight:600;color:${tokens.textPrimary}">${p.value?.toLocaleString()}</span>
          </div>`;
        });
        return res;
      },
    },
    legend: {
      data: [
        { name: "Approved Intake", icon: "roundRect" },
        { name: "Actual Enrolled", icon: "diamond" },
      ],
      bottom: 0,
      textStyle: { fontSize: 11, color: tokens.textSecondary },
    },
    grid: {
      left: "3%",
      right: "3%",
      bottom: "16%",
      top: "10%",
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: states,
      axisLabel: {
        rotate: 30,
        fontSize: 10,
        color: tokens.textSecondary,
      },
      axisLine: { lineStyle: { color: tokens.axisLine } },
    },
    yAxis: {
      type: "value",
      axisLabel: { fontSize: 10, color: tokens.textSecondary },
      splitLine: { lineStyle: { color: tokens.splitLine, type: "dashed" } },
    },
    series: [
      {
        name: "Approved Intake",
        type: "bar",
        data: intake,
        itemStyle: {
          color: tokens.primary,
          borderRadius: [4, 4, 0, 0],
          borderWidth: 1,
          borderColor: tokens.primary,
        },
        label: {
          show: true,
          position: "top",
          fontSize: 9,
          color: tokens.textSecondary,
          formatter: (p: any) => (p.value > 0 ? `${p.value}` : ""),
        },
      },
      {
        name: "Actual Enrolled",
        type: "bar",
        data: enrolled,
        itemStyle: {
          color: tokens.success,
          borderRadius: [4, 4, 0, 0],
          borderWidth: 1,
          borderColor: tokens.success,
        },
        label: {
          show: true,
          position: "top",
          fontSize: 9,
          color: tokens.textSecondary,
          formatter: (p: any) => (p.value > 0 ? `${p.value}` : ""),
        },
      },
    ],
  };

  return (
    <AccessibleChartCard
      title="State-Level Intake vs Actual Enrolment"
      subtitle="Comparative analysis of approved seat capacity against actual admissions"
      icon="domain"
      summary={summary}
      tableHeaders={tableHeaders}
      tableRows={tableRows}
      headerRight={headerRight}
    >
      <ReactECharts
        theme={UX4G_CHART_THEME}
        option={option}
        style={{ height: `${height}px`, width: "100%" }}
        notMerge
        lazyUpdate
      />
    </AccessibleChartCard>
  );
}
