import React from "react";
import ReactECharts from "echarts-for-react";
import type { SubmissionProgressCounts } from "../types/analytics";
import { getChartThemeTokens, registerUx4gTheme, UX4G_CHART_THEME } from "./echartsTheme";
import { AccessibleChartCard } from "./AccessibleChartCard";

interface SubmissionProgressChartProps {
  counts: SubmissionProgressCounts;
  height?: number;
  headerRight?: React.ReactNode;
}

export function SubmissionProgressChart({
  counts,
  height = 300,
  headerRight,
}: SubmissionProgressChartProps) {
  registerUx4gTheme();
  const tokens = getChartThemeTokens();

  const safeCounts: SubmissionProgressCounts = {
    draft: counts?.draft || 0,
    submitted_clean: counts?.submitted_clean || 0,
    submitted_with_exceptions: counts?.submitted_with_exceptions || 0,
    under_review: counts?.under_review || 0,
    query_raised: counts?.query_raised || 0,
    accepted: counts?.accepted || 0,
    escalated: counts?.escalated || 0,
    not_started: counts?.not_started || 0,
    total_eligible: counts?.total_eligible || 0,
  };

  const rawData = [
    { name: "Accepted", value: safeCounts.accepted, color: tokens.success, icon: "roundRect" },
    { name: "Submitted Clean", value: safeCounts.submitted_clean, color: tokens.primary, icon: "circle" },
    {
      name: "Submitted w/ Exceptions",
      value: safeCounts.submitted_with_exceptions,
      color: tokens.accent,
      icon: "diamond",
    },
    { name: "Under Review", value: safeCounts.under_review, color: tokens.purple, icon: "triangle" },
    { name: "Query Raised", value: safeCounts.query_raised, color: tokens.secondary, icon: "rect" },
    { name: "Escalated", value: safeCounts.escalated, color: tokens.error, icon: "pin" },
    { name: "In Draft", value: safeCounts.draft, color: tokens.neutral, icon: "circle" },
    { name: "Not Started", value: safeCounts.not_started, color: tokens.splitLine, icon: "roundRect" },
  ];

  const chartData = rawData
    .filter((item) => item.value > 0)
    .map((item) => ({
      name: item.name,
      value: item.value,
      itemStyle: {
        color: item.color,
        borderWidth: 2,
        borderColor: "var(--edutrace-surface-page)",
      },
    }));

  const totalColleges = rawData.reduce((acc, item) => acc + (item.value || 0), 0);

  const summary = totalColleges > 0
    ? `Submission lifecycle status across ${totalColleges} institutions: ${safeCounts.accepted} accepted, ${safeCounts.submitted_clean} clean, ${safeCounts.submitted_with_exceptions} with exceptions, and ${safeCounts.under_review} in active AICTE review.`
    : "No submission metrics recorded for this academic year.";

  const tableHeaders = ["Submission Status", "Colleges Count", "Share"];
  const tableRows = rawData
    .filter((item) => item.value > 0)
    .map((item) => [
      item.name,
      item.value,
      `${totalColleges > 0 ? Math.round((item.value / totalColleges) * 100) : 0}%`,
    ]);

  const option = {
    tooltip: {
      trigger: "item",
      backgroundColor: "var(--edutrace-surface-page)",
      borderColor: tokens.axisLine,
      borderWidth: 1,
      textStyle: { color: tokens.textPrimary, fontSize: 12 },
      formatter: "{b}: <b>{c}</b> institutions ({d}%)",
    },
    legend: {
      orient: "horizontal",
      bottom: 0,
      textStyle: { fontSize: 10, color: tokens.textSecondary },
      itemWidth: 10,
      itemHeight: 10,
    },
    series: [
      {
        name: "Submission Status",
        type: "pie",
        radius: ["42%", "70%"],
        center: ["50%", "45%"],
        avoidLabelOverlap: true,
        label: {
          show: true,
          position: "outside",
          formatter: "{b}: {c}",
          fontSize: 10,
          color: tokens.textSecondary,
        },
        labelLine: {
          show: true,
          lineStyle: { color: tokens.axisLine },
        },
        data: chartData,
      },
    ],
  };

  return (
    <AccessibleChartCard
      title="Submission Progress"
      subtitle={`Status breakdown across ${totalColleges} eligible colleges`}
      icon="fact_check"
      summary={summary}
      tableHeaders={tableHeaders}
      tableRows={tableRows}
      headerRight={headerRight}
      minTableWidth="min-w-[320px]"
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
