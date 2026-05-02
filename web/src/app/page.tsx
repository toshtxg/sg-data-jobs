import { BarChart3, Clock } from "lucide-react";
import {
  compactListingsForClient,
  loadClassifiedListings,
  loadLatestPullTimestamp,
} from "@/lib/data";
import {
  buildPostingTrend,
  compactSalary,
  countBy,
  formatAge,
  formatDate,
  isDataRole,
  isRecentListing,
  skillCounts,
} from "@/lib/market";
import { assignSalaryBin, SALARY_BINS } from "@/lib/salary";
import { HorizontalBars, PostingTrend, VerticalBars } from "@/components/charts";
import { DataCaveat } from "@/components/data-caveat";
import {
  SalaryDistribution,
  type SalaryDistributionJob,
} from "@/components/salary-distribution";
import { Badge, EmptyState, MetricCard, PageHeader, Panel, SectionTitle } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const [listings, latestPull] = await Promise.all([
    loadClassifiedListings(),
    loadLatestPullTimestamp(),
  ]);
  const clientListings = compactListingsForClient(listings);
  const recent = clientListings
    .filter((row) => row.role_category !== "Other" && isRecentListing(row))
    .sort((a, b) => String(b.raw.posting_date).localeCompare(String(a.raw.posting_date)))
    .slice(0, 20);
  const roleCounts = Object.fromEntries(countBy(clientListings, (row) => row.role_category));
  const chartRoles = Object.entries(roleCounts)
    .filter(([role]) => role !== "Other")
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value }));
  const topSkills = skillCounts(clientListings, 15);
  const topSkill = topSkills[0];
  const topRole = chartRoles[0]?.name || "N/A";
  const dataScopeCount = Object.entries(roleCounts).reduce(
    (total, [role, count]) => total + (isDataRole(role) ? count : 0),
    0,
  );
  const postingTrend = buildPostingTrend(clientListings);

  const salaryBinCounts: Record<string, number> = Object.fromEntries(
    SALARY_BINS.map((bin) => [bin.label, 0]),
  );
  const salaryBinJobs: Record<string, SalaryDistributionJob[]> =
    Object.fromEntries(
      SALARY_BINS.map((bin) => [bin.label, [] as SalaryDistributionJob[]]),
    );
  let noSalaryCount = 0;
  for (const row of clientListings) {
    if (row.role_category === "Other") continue;
    const bin = assignSalaryBin(row.raw.salary_min, row.raw.salary_max);
    if (bin === null) {
      noSalaryCount += 1;
      continue;
    }
    salaryBinCounts[bin] = (salaryBinCounts[bin] ?? 0) + 1;
    salaryBinJobs[bin].push({
      id: row.id || `${row.raw.source_url ?? ""}-${row.raw.title ?? ""}`,
      title: row.raw.title ?? "",
      company: row.raw.company ?? "Unknown",
      role: row.role_category ?? "",
      seniority: row.seniority_level ?? "",
      salary_min: row.raw.salary_min,
      salary_max: row.raw.salary_max,
      posting_date: row.raw.posting_date ?? null,
      source_url: row.raw.source_url ?? null,
    });
  }
  for (const label of Object.keys(salaryBinJobs)) {
    salaryBinJobs[label].sort((a, b) =>
      (b.posting_date ?? "").localeCompare(a.posting_date ?? ""),
    );
  }

  return (
    <>
      <PageHeader title="Singapore Data & AI Job Pulse" eyebrow="Live market dashboard">
        <div className="flex items-center gap-2 rounded-md border border-line bg-panel px-3 py-2 text-sm text-muted">
          <Clock size={16} />
          Latest pull {latestPull ? formatAge(latestPull) : "unknown"}
        </div>
      </PageHeader>

      <DataCaveat />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Tracked listings" value={clientListings.length.toLocaleString()} detail="Classified jobs in Supabase" />
        <MetricCard label="New this week" value={recent.length.toLocaleString()} detail="Based on posting date" />
        <MetricCard label="Top data role" value={topRole} detail="Excludes non-data roles" />
        <MetricCard label="Top skill" value={topSkill?.name || "N/A"} detail={topSkill ? `${topSkill.value} mentions` : "No skill data"} />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <Panel>
          <SectionTitle>Listings By Role</SectionTitle>
          {chartRoles.length ? <HorizontalBars data={chartRoles} /> : <EmptyState>No role data available.</EmptyState>}
        </Panel>
        <Panel>
          <SectionTitle>Top Technical Skills</SectionTitle>
          <VerticalBars data={topSkills.slice(0, 12)} />
        </Panel>
      </div>

      <div className="mt-6">
        <Panel>
          <SectionTitle>Salary Distribution</SectionTitle>
          <SalaryDistribution
            binCounts={salaryBinCounts}
            binJobs={salaryBinJobs}
            noSalaryCount={noSalaryCount}
          />
        </Panel>
      </div>

      <div className="mt-6">
        <Panel>
          <SectionTitle>New This Week</SectionTitle>
          {recent.length ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="text-left text-xs uppercase text-muted">
                  <tr>
                    <th className="py-2 pr-4">Role</th>
                    <th className="py-2 pr-4">Company</th>
                    <th className="py-2 pr-4">Type</th>
                    <th className="py-2 pr-4">Salary</th>
                    <th className="py-2 pr-4">Posted</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {recent.map((row) => (
                    <tr key={row.id || row.raw.source_url}>
                      <td className="py-3 pr-4">
                        <a href={row.raw.source_url || "#"} target="_blank" rel="noreferrer" className="font-medium text-foreground hover:text-accent">
                          {row.raw.title || "Untitled role"}
                        </a>
                      </td>
                      <td className="py-3 pr-4 text-muted">{row.raw.company || "Unknown"}</td>
                      <td className="py-3 pr-4"><Badge>{row.role_category}</Badge></td>
                      <td className="py-3 pr-4 text-muted">{compactSalary(row.raw.salary_min, row.raw.salary_max)}</td>
                      <td className="py-3 pr-4 text-muted">{formatDate(row.raw.posting_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState>No recent listings found.</EmptyState>
          )}
        </Panel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[0.7fr_1.3fr]">
        <Panel>
          <SectionTitle>Role Scope</SectionTitle>
          <div className="flex items-center gap-3 text-sm text-muted">
            <BarChart3 size={18} className="text-accent" />
            {dataScopeCount.toLocaleString()} listings sit in the default data and analytics scope.
          </div>
        </Panel>
        <Panel>
          <SectionTitle>Posting Activity</SectionTitle>
          {postingTrend.length ? <PostingTrend data={postingTrend} /> : <EmptyState>No posting dates available yet.</EmptyState>}
        </Panel>
      </div>
    </>
  );
}
