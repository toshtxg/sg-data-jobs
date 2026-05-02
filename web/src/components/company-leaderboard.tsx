"use client";

import { useMemo, useState } from "react";
import { ExternalLink } from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { compactSalary, countBy, formatDate, skillCounts, topCounts } from "@/lib/market";
import type { ClassifiedListing } from "@/lib/types";
import { HorizontalBars, VerticalBars } from "@/components/charts";
import { Badge, EmptyState, Panel, SectionTitle } from "@/components/ui";

function formatMonth(yyyyMm: string) {
  const [year, month] = yyyyMm.split("-");
  return new Date(Number(year), Number(month) - 1, 1).toLocaleDateString("en-SG", {
    month: "short",
    year: "2-digit",
  });
}

export function CompanyLeaderboard({ listings }: { listings: ClassifiedListing[] }) {
  const companies = useMemo(() => {
    return topCounts(
      countBy(
        listings.filter((row) => row.role_category !== "Other"),
        (row) => row.raw.company,
      ),
      50,
    );
  }, [listings]);

  const [selected, setSelected] = useState(companies[0]?.name || "");

  const companyRows = listings
    .filter((row) => row.raw.company === selected && row.role_category !== "Other")
    .sort((a, b) => String(b.raw.posting_date).localeCompare(String(a.raw.posting_date)));

  const roleBars = topCounts(countBy(companyRows, (row) => row.role_category), 10);
  const skills = skillCounts(companyRows, 12);

  const timeline = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of companyRows) {
      const date = row.raw.posting_date;
      if (!date) continue;
      const month = date.slice(0, 7);
      counts.set(month, (counts.get(month) || 0) + 1);
    }
    return [...counts.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([month, count]) => ({ month, label: formatMonth(month), count }));
  }, [companyRows]);

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Panel>
          <SectionTitle>Company Rankings</SectionTitle>
          <div className="max-h-[520px] space-y-2 overflow-y-auto pr-1">
            {companies.map((company, index) => (
              <button
                key={company.name}
                onClick={() => setSelected(company.name)}
                className={`flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm ${
                  selected === company.name
                    ? "border-accent bg-panel-strong text-foreground"
                    : "border-line text-muted hover:text-foreground"
                }`}
              >
                <span>
                  {index + 1}. {company.name}
                </span>
                <span>{company.value}</span>
              </button>
            ))}
          </div>
        </Panel>

        <div className="space-y-4">
          <Panel>
            <SectionTitle>{selected || "Company"} Profile</SectionTitle>
            {companyRows.length ? (
              <>
                <div className="grid gap-4 lg:grid-cols-3">
                  <div className="rounded-lg border border-line bg-panel-strong p-3">
                    <div className="text-sm text-muted">Total postings</div>
                    <div className="mt-1 text-2xl font-semibold">{companyRows.length}</div>
                  </div>
                  <div className="rounded-lg border border-line bg-panel-strong p-3">
                    <div className="text-sm text-muted">Top role</div>
                    <div className="mt-1 text-lg font-semibold">{roleBars[0]?.name || "N/A"}</div>
                  </div>
                  <div className="rounded-lg border border-line bg-panel-strong p-3">
                    <div className="text-sm text-muted">Top skill</div>
                    <div className="mt-1 text-lg font-semibold">{skills[0]?.name || "N/A"}</div>
                  </div>
                </div>
                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <HorizontalBars data={roleBars} />
                  <VerticalBars data={skills.slice(0, 8)} />
                </div>
              </>
            ) : (
              <EmptyState>Select a company with active listings.</EmptyState>
            )}
          </Panel>

          {timeline.length > 1 && (
            <Panel>
              <SectionTitle>Posting History</SectionTitle>
              <p className="mb-3 text-xs text-muted">
                Monthly job postings — shows hiring cadence and recent activity spikes.
              </p>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={timeline} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 11, fill: "var(--color-muted)" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 11, fill: "var(--color-muted)" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "var(--color-panel-strong)",
                      border: "1px solid var(--color-line)",
                      borderRadius: "6px",
                      fontSize: "12px",
                    }}
                    formatter={(value) => [value, "Postings"]}
                    labelFormatter={(label) => label}
                  />
                  <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                    {timeline.map((entry, index) => (
                      <Cell
                        key={entry.month}
                        fill={
                          index === timeline.length - 1
                            ? "var(--color-accent)"
                            : "var(--color-accent)"
                        }
                        fillOpacity={index === timeline.length - 1 ? 1 : 0.55}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Panel>
          )}
        </div>
      </div>

      <Panel>
        <SectionTitle>All Postings</SectionTitle>
        {companyRows.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-xs uppercase text-muted">
                <tr>
                  <th className="py-2 pr-4">Title</th>
                  <th className="py-2 pr-4">Role</th>
                  <th className="py-2 pr-4">Salary</th>
                  <th className="py-2 pr-4">Posted</th>
                  <th className="py-2 pr-4">Apply</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {companyRows.slice(0, 50).map((row) => (
                  <tr key={row.id || row.raw.source_url}>
                    <td className="py-3 pr-4 font-medium">{row.raw.title || "Untitled"}</td>
                    <td className="py-3 pr-4">
                      <Badge>{row.role_category}</Badge>
                    </td>
                    <td className="py-3 pr-4 text-muted">
                      {compactSalary(row.raw.salary_min, row.raw.salary_max)}
                    </td>
                    <td className="py-3 pr-4 text-muted">{formatDate(row.raw.posting_date)}</td>
                    <td className="py-3 pr-4">
                      {row.raw.source_url && (
                        <a
                          href={row.raw.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-accent"
                        >
                          <ExternalLink size={16} />
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState>No postings found.</EmptyState>
        )}
      </Panel>
    </div>
  );
}
