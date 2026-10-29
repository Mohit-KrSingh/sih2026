import React from "react";
import ReactECharts from "echarts-for-react";
import type { CourseMetricsItem } from "../types/analytics";
import { getChartThemeTokens, registerUx4gTheme, UX4G_CHART_THEME } from "./echartsTheme";
import { AccessibleChartCard } from "./AccessibleChartCard";

interface CourseDistributionChartProps {
  data: CourseMetricsItem[];
  height?: number;
  headerRight?: React.ReactNode;
}

export function CourseDistributionChart({
  data,
  height = 280,
  headerRight,
}: CourseDistributionChartProps) {
  registerUx4gTheme();
  const tokens = getChartThemeTokens();

  // Take top 8 courses by approved intake
  const topCourses = [...data]
    .sort((a, b) => b.approved_intake - a.approved_intake)
    .slice(0, 8);

  const names = topCourses.map((c) =>
    c.course_name.length > 24 ? c.course_name.substring(0, 22) + "..." : c.course_name
  );
  const intake = topCourses.map((c) => c.approved_intake);
  const enrolled = topCourses.map((c) => c.total_enrolled);

  const totalIntake = intake.reduce((a, b) => a + b, 0);
  const totalEnrolled = enrolled.reduce((a, b) => a + b, 0);
  const overallUtilisation =
    totalIntake > 0 ? Math.round((totalEnrolled / totalIntake) * 100) : 0;

  const topCourse = topCourses[0];

  const summary = topCourses.length > 0
    ? `Top ${topCourses.length} academic courses represent ${totalIntake.toLocaleString()} approved seats with ${totalEnrolled.toLocaleString()} enrolled students (${overallUtilisation}% seat utilisation). ${topCourse ? `${topCourse.course_name} leads intake capacity with ${topCourse.approved_intake.toLocaleString()} seats.` : ""}`
    : "No course metrics recorded for this academic year.";

  const tableHeaders = ["Discipline / Course", "Approved Intake", "Enrolled Students", "Utilisation"];
  const tableRows = topCourses.map((c) => [
    c.course_name,
    c.approved_intake,
    c.total_enrolled,
    `${c.approved_intake > 0 ? Math.round((c.total_enrolled / c.approved_intake) * 100) : 0}%`,
  ]);

  const option = {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "var(--edutrace-surface-page)",
      borderColor: tokens.axisLine,
      borderWidth: 1,
      textStyle: { color: tokens.textPrimary, fontSize: 12 },
    },
    legend: {
      data: [
        { name: "Approved Intake", icon: "roundRect" },
        { name: "Enrolled Students", icon: "circle" },
      ],
      bottom: 0,
      textStyle: { fontSize: 11, color: tokens.textSecondary },
    },
    grid: {
      left: "3%",
      right: "8%",
      bottom: "14%",
      top: "5%",
      containLabel: true,
    },
    xAxis: {
      type: "value",
      axisLabel: { fontSize: 10, color: tokens.textSecondary },
      splitLine: { lineStyle: { color: tokens.splitLine, type: "dashed" } },
    },
    yAxis: {
      type: "category",
      data: [...names].reverse(),
      axisLabel: { fontSize: 10, color: tokens.textSecondary },
      axisLine: { lineStyle: { color: tokens.axisLine } },
    },
    series: [
      {
        name: "Approved Intake",
        type: "bar",
        data: [...intake].reverse(),
        itemStyle: {
          color: tokens.primary,
          borderRadius: [0, 4, 4, 0],
          borderWidth: 1,
          borderColor: tokens.primary,
        },
        label: {
          show: true,
          position: "right",
          fontSize: 9,
          color: tokens.textSecondary,
          formatter: (p: any) => (p.value > 0 ? `${p.value}` : ""),
        },
      },
      {
        name: "Enrolled Students",
        type: "bar",
        data: [...enrolled].reverse(),
        itemStyle: {
          color: tokens.secondary,
          borderRadius: [0, 4, 4, 0],
          borderWidth: 1,
          borderColor: tokens.secondary,
        },
        label: {
          show: true,
          position: "right",
          fontSize: 9,
          color: tokens.textSecondary,
          formatter: (p: any) => (p.value > 0 ? `${p.value}` : ""),
        },
      },
    ],
  };

  return (
    <AccessibleChartCard
      title="Course Discipline Seat Capacity & Enrolment"
      subtitle="Distribution across top academic disciplines and engineering programs"
      icon="school"
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
