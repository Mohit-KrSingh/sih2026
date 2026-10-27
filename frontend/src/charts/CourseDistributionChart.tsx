import ReactECharts from "echarts-for-react";
import type { CourseMetricsItem } from "../types/analytics";

interface CourseDistributionChartProps {
  data: CourseMetricsItem[];
  height?: number;
}

export function CourseDistributionChart({ data, height = 320 }: CourseDistributionChartProps) {
  // Take top 8 courses by approved intake
  const topCourses = [...data]
    .sort((a, b) => b.approved_intake - a.approved_intake)
    .slice(0, 8);

  const names = topCourses.map((c) =>
    c.course_name.length > 24 ? c.course_name.substring(0, 22) + "..." : c.course_name
  );
  const intake = topCourses.map((c) => c.approved_intake);
  const enrolled = topCourses.map((c) => c.total_enrolled);

  const option = {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    legend: {
      data: ["Approved Intake", "Enrolled Students"],
      bottom: 0,
      textStyle: { fontSize: 11, color: "#475569" },
    },
    grid: {
      left: "3%",
      right: "5%",
      bottom: "12%",
      top: "5%",
      containLabel: true,
    },
    xAxis: {
      type: "value",
      axisLabel: { fontSize: 10, color: "#64748b" },
      splitLine: { lineStyle: { color: "#f1f5f9" } },
    },
    yAxis: {
      type: "category",
      data: names.reverse(),
      axisLabel: { fontSize: 10, color: "#334155" },
      axisLine: { lineStyle: { color: "#cbd5e1" } },
    },
    series: [
      {
        name: "Approved Intake",
        type: "bar",
        data: intake.reverse(),
        itemStyle: { color: "#4f46e5", borderRadius: [0, 4, 4, 0] },
      },
      {
        name: "Enrolled Students",
        type: "bar",
        data: enrolled.reverse(),
        itemStyle: { color: "#06b6d4", borderRadius: [0, 4, 4, 0] },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: `${height}px`, width: "100%" }} notMerge lazyUpdate />;
}
