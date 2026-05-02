"use client";

import { useState, useSyncExternalStore } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ROLE_COLORS } from "@/lib/constants";
import { formatSalaryRange, SALARY_BINS } from "@/lib/salary";
import { safeJobSourceUrl } from "@/lib/security";

const axis = { fill: "#a1a1aa", fontSize: 12 };
const grid = "rgba(255,255,255,0.08)";

const noopSubscribe = () => () => {};
const clientSnapshot = () => true;
const serverSnapshot = () => false;

function useMounted() {
  return useSyncExternalStore(noopSubscribe, clientSnapshot, serverSnapshot);
}

export type SalaryDistributionJob = {
  id: string;
  title: string;
  company: string;
  role: string;
  seniority: string;
  salary_min: number | string | null;
  salary_max: number | string | null;
  posting_date: string | null;
  source_url: string | null;
};

export function SalaryDistribution({
  binCounts,
  binJobs,
  noSalaryCount,
}: {
  binCounts: Record<string, number>;
  binJobs: Record<string, SalaryDistributionJob[]>;
  noSalaryCount: number;
}) {
  const mounted = useMounted();
  const [selectedBin, setSelectedBin] = useState<string | null>(null);

  const data = SALARY_BINS.map((bin, index) => ({
    name: bin.label,
    value: binCounts[bin.label] ?? 0,
    fill: ROLE_COLORS[index % ROLE_COLORS.length],
  }));

  const totalWithSalary = data.reduce((acc, d) => acc + d.value, 0);
  const selectedJobs = selectedBin ? binJobs[selectedBin] ?? [] : [];

  return (
    <div>
      <div className="mb-3 text-xs text-muted">
        {totalWithSalary.toLocaleString()} listings with salary disclosed ·{" "}
        {noSalaryCount.toLocaleString()} listings did not disclose a salary range
      </div>
      <div className="h-[320px] w-full">
        {mounted ? (
          <ResponsiveContainer>
            <BarChart
              data={data}
              margin={{ left: 8, right: 16, top: 8, bottom: 24 }}
              onClick={(e) => {
                const label =
                  e && typeof e === "object" && "activeLabel" in e
                    ? (e as { activeLabel?: string }).activeLabel
                    : undefined;
                if (label) {
                  setSelectedBin((prev) => (prev === label ? null : label));
                }
              }}
            >
              <CartesianGrid stroke={grid} vertical={false} />
              <XAxis dataKey="name" tick={axis} />
              <YAxis tick={axis} allowDecimals={false} />
              <Tooltip
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
                contentStyle={{ background: "#181a20", border: "1px solid #30343d" }}
                formatter={(value) => [`${Number(value)} listings`, "Count"]}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {data.map((entry) => (
                  <Cell
                    key={entry.name}
                    fill={entry.fill}
                    fillOpacity={
                      selectedBin === null || selectedBin === entry.name ? 1 : 0.35
                    }
                    stroke={selectedBin === entry.name ? "#fafafa" : undefined}
                    strokeWidth={selectedBin === entry.name ? 2 : 0}
                    cursor="pointer"
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div
            className="flex w-full items-center justify-center rounded-md border border-line bg-panel-strong text-sm text-muted"
            style={{ height: 320 }}
          >
            Loading chart
          </div>
        )}
      </div>

      {selectedBin ? (
        <div className="mt-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">
              {selectedJobs.length} jobs in {selectedBin} band
            </h3>
            <button
              type="button"
              onClick={() => setSelectedBin(null)}
              className="text-xs text-muted hover:text-foreground"
            >
              Clear
            </button>
          </div>
          {selectedJobs.length ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="text-left text-xs uppercase text-muted">
                  <tr>
                    <th className="py-2 pr-4">Role</th>
                    <th className="py-2 pr-4">Company</th>
                    <th className="py-2 pr-4">Seniority</th>
                    <th className="py-2 pr-4">Salary</th>
                    <th className="py-2 pr-4">Posted</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {selectedJobs.slice(0, 50).map((job) => {
                    const sourceUrl = safeJobSourceUrl(job.source_url);

                    return (
                      <tr key={job.id}>
                        <td className="py-2 pr-4">
                          {sourceUrl ? (
                            <a
                              href={sourceUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-medium text-foreground hover:text-accent"
                            >
                              {job.title || "Untitled role"}
                            </a>
                          ) : (
                            <span className="font-medium text-foreground">
                              {job.title || "Untitled role"}
                            </span>
                          )}
                          <div className="text-xs text-muted">{job.role}</div>
                        </td>
                        <td className="py-2 pr-4 text-muted">{job.company || "Unknown"}</td>
                        <td className="py-2 pr-4 text-muted">{job.seniority || "—"}</td>
                        <td className="py-2 pr-4 text-muted">
                          {formatSalaryRange(job.salary_min, job.salary_max)}
                        </td>
                        <td className="py-2 pr-4 text-muted">
                          {job.posting_date || "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {selectedJobs.length > 50 ? (
                <div className="mt-2 text-xs text-muted">
                  Showing 50 of {selectedJobs.length} jobs in this band.
                </div>
              ) : null}
            </div>
          ) : (
            <div className="rounded-md border border-dashed border-line bg-panel p-4 text-center text-sm text-muted">
              No jobs in this band.
            </div>
          )}
        </div>
      ) : (
        <div className="mt-3 text-xs text-muted">
          Click a bar to see the jobs in that salary band.
        </div>
      )}
    </div>
  );
}
