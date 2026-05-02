"use client";

import { useSyncExternalStore } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ROLE_COLORS } from "@/lib/constants";
import type { ChartDatum, PostingTrendPoint } from "@/lib/types";

const axis = { fill: "#a1a1aa", fontSize: 12 };
const grid = "rgba(255,255,255,0.08)";

const noopSubscribe = () => () => {};
const clientSnapshot = () => true;
const serverSnapshot = () => false;

function useMounted() {
  return useSyncExternalStore(noopSubscribe, clientSnapshot, serverSnapshot);
}

function ChartFallback({ height }: { height: number }) {
  return (
    <div
      className="flex w-full items-center justify-center rounded-md border border-line bg-panel-strong text-sm text-muted"
      style={{ height }}
    >
      Loading chart
    </div>
  );
}

export function HorizontalBars({ data }: { data: ChartDatum[] }) {
  const mounted = useMounted();
  if (!mounted) return <ChartFallback height={360} />;
  return (
    <div className="h-[360px] w-full">
      <ResponsiveContainer>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ left: 18, right: 24, top: 8, bottom: 8 }}
        >
          <CartesianGrid stroke={grid} horizontal={false} />
          <XAxis type="number" tick={axis} />
          <YAxis dataKey="name" type="category" width={128} tick={axis} />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            contentStyle={{ background: "#181a20", border: "1px solid #30343d" }}
          />
          <Bar dataKey="value" fill={ROLE_COLORS[0]} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function VerticalBars({ data }: { data: ChartDatum[] }) {
  const mounted = useMounted();
  if (!mounted) return <ChartFallback height={320} />;
  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: 8, right: 8, top: 8, bottom: 40 }}>
          <CartesianGrid stroke={grid} vertical={false} />
          <XAxis dataKey="name" tick={axis} angle={-30} textAnchor="end" height={72} />
          <YAxis tick={axis} />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            contentStyle={{ background: "#181a20", border: "1px solid #30343d" }}
          />
          <Bar dataKey="value" fill={ROLE_COLORS[1]} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function PostingTrend({ data }: { data: PostingTrendPoint[] }) {
  const mounted = useMounted();
  if (!mounted) return <ChartFallback height={300} />;
  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ left: 8, right: 16, top: 8, bottom: 24 }}>
          <CartesianGrid stroke={grid} vertical={false} />
          <XAxis dataKey="date" tick={axis} />
          <YAxis tick={axis} />
          <Tooltip
            contentStyle={{ background: "#181a20", border: "1px solid #30343d" }}
          />
          <Line
            type="monotone"
            dataKey="daily"
            name="Daily postings"
            stroke={ROLE_COLORS[1]}
            strokeWidth={2}
          />
          <Line
            type="monotone"
            dataKey="rolling_average"
            name="7d average"
            stroke={ROLE_COLORS[0]}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function MatrixHeatmap({
  rows,
}: {
  rows: { skill: string; values: { level: string; value: number }[] }[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-1 text-sm">
        <thead>
          <tr>
            <th className="sticky left-0 bg-panel px-2 py-2 text-left text-muted">
              Skill
            </th>
            {rows[0]?.values.map((item) => (
              <th key={item.level} className="px-2 py-2 text-left text-muted">
                {item.level}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.skill}>
              <td className="sticky left-0 bg-panel px-2 py-2 text-foreground">
                {row.skill}
              </td>
              {row.values.map((item) => (
                <td key={item.level} className="min-w-24 px-1 py-1">
                  <div
                    className="rounded-md px-2 py-2 text-xs text-foreground"
                    style={{
                      background: `rgba(45, 212, 191, ${Math.max(item.value, 8) / 100})`,
                    }}
                  >
                    {item.value}%
                  </div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
