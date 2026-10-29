import ReactECharts from "echarts-for-react";
import type { StateMetricsItem } from "../types/analytics";

interface StateIntakeChartProps {
  data: StateMetricsItem[];
  height?: number;
}

export function StateIntakeChart({ data, height = 320 }: StateIntakeChartProps) {
  const states = data.map((d) => d.state);
  const intake = data.map((d) => d.approved_intake);
  const enrolled = data.map((d) => d.total_enrolled);

  const option = {
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params: any[]) => {
        const stateName = params[0]?.name || "";
        let res = `<div style="font-weight:600;margin-bottom:4px;">${stateName}</div>`;
        params.forEach((p) => {
          res += `<div style="display:flex;justify-content:space-between;gap:12px;font-size:12px;">
            <span><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:6px;"></span>${p.seriesName}</span>
            <span style="font-weight:600;">${p.value?.toLocaleString()}</span>
          </div>`;
        });
        return res;
      },
    },
    legend: {
      data: ["Approved Intake", "Actual Enrolled"],
      bottom: 0,
      textStyle: { fontSize: 11, color: "#475569" },
    },
    grid: {
      left: "3%",
      right: "3%",
      bottom: "12%",
      top: "8%",
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: states,
      axisLabel: {
        rotate: 30,
        fontSize: 10,
        color: "#64748b",
      },
      axisLine: { lineStyle: { color: "#cbd5e1" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { fontSize: 10, color: "#64748b" },
      splitLine: { lineStyle: { color: "#f1f5f9" } },
    },
    series: [
      {
        name: "Approved Intake",
        type: "bar",
        data: intake,
        itemStyle: { color: "#4338ca", borderRadius: [4, 4, 0, 0] },
      },
      {
        name: "Actual Enrolled",
        type: "bar",
        data: enrolled,
        itemStyle: { color: "#059669", borderRadius: [4, 4, 0, 0] },
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: `${height}px`, width: "100%" }} notMerge lazyUpdate />;
}
