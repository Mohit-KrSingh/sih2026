import ReactECharts from "echarts-for-react";
import type { SubmissionProgressCounts } from "../types/analytics";

interface SubmissionProgressChartProps {
  counts: SubmissionProgressCounts;
  height?: number;
}

export function SubmissionProgressChart({ counts, height = 300 }: SubmissionProgressChartProps) {
  const chartData = [
    { value: counts.accepted, name: "Accepted", itemStyle: { color: "#10b981" } },
    { value: counts.submitted_clean, name: "Submitted Clean", itemStyle: { color: "#3b82f6" } },
    { value: counts.submitted_with_exceptions, name: "Submitted w/ Exceptions", itemStyle: { color: "#f59e0b" } },
    { value: counts.under_review, name: "Under Review", itemStyle: { color: "#6366f1" } },
    { value: counts.query_raised, name: "Query Raised", itemStyle: { color: "#ec4899" } },
    { value: counts.escalated, name: "Escalated", itemStyle: { color: "#ef4444" } },
    { value: counts.draft, name: "In Draft", itemStyle: { color: "#94a3b8" } },
    { value: counts.not_started, name: "Not Started", itemStyle: { color: "#cbd5e1" } },
  ].filter((item) => item.value > 0);

  const option = {
    tooltip: {
      trigger: "item",
      formatter: "{b}: <b>{c}</b> colleges ({d}%)",
    },
    legend: {
      orient: "horizontal",
      bottom: 0,
      textStyle: { fontSize: 10, color: "#475569" },
      itemWidth: 10,
      itemHeight: 10,
    },
    series: [
      {
        name: "Submission Status",
        type: "pie",
        radius: ["42%", "70%"],
        center: ["50%", "45%"],
        avoidLabelOverlap: false,
        label: {
          show: false,
          position: "center",
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: "bold",
            formatter: "{b}\n{c}",
          },
        },
        labelLine: {
          show: false,
        },
        data: chartData,
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: `${height}px`, width: "100%" }} notMerge lazyUpdate />;
}
