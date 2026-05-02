"use client";

import { useMemo, useState } from "react";
import { ExternalLink, Target } from "lucide-react";
import { ROLE_CATEGORIES, SENIORITY_LEVELS, WORK_MODES } from "@/lib/constants";
import { compactSalary, formatDate, uniqueSkills } from "@/lib/market";
import { safeJobSourceUrl } from "@/lib/security";
import type { ClassifiedListing } from "@/lib/types";
import { Badge, EmptyState, Panel } from "@/components/ui";

type MatchRow = {
  listing: ClassifiedListing;
  matched: string[];
  missing: string[];
  pct: number;
};

export function JobsForYou({ listings }: { listings: ClassifiedListing[] }) {
  const skillOptions = useMemo(() => uniqueSkills(listings).slice(0, 80), [listings]);
  const [skillsText, setSkillsText] = useState("Python, SQL, Tableau");
  const [role, setRole] = useState("");
  const [seniority, setSeniority] = useState("");
  const [workMode, setWorkMode] = useState("");

  const userSkills = useMemo(
    () =>
      new Set(
        skillsText
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      ),
    [skillsText],
  );

  const matches = useMemo(() => {
    const userLower = new Set([...userSkills].map((skill) => skill.toLowerCase()));
    const scored: MatchRow[] = [];
    for (const listing of listings) {
      if (listing.role_category === "Other") continue;
      if (role && listing.role_category !== role) continue;
      if (seniority && listing.seniority_level !== seniority) continue;
      if (workMode && listing.remote_hybrid_onsite !== workMode) continue;
      const listingSkills = (listing.technical_skills || []).filter(Boolean);
      if (!listingSkills.length) continue;
      const matched = listingSkills.filter((skill) => userLower.has(skill.toLowerCase()));
      if (!matched.length) continue;
      const missing = listingSkills.filter((skill) => !userLower.has(skill.toLowerCase()));
      scored.push({
        listing,
        matched,
        missing,
        pct: matched.length / listingSkills.length,
      });
    }
    return scored.sort((a, b) => b.pct - a.pct || String(b.listing.raw.posting_date).localeCompare(String(a.listing.raw.posting_date)));
  }, [listings, role, seniority, userSkills, workMode]);

  const strong = matches.filter((match) => match.pct >= 0.5);
  const partial = matches.filter((match) => match.pct < 0.5);
  const missingCounts = new Map<string, number>();
  for (const match of matches) {
    for (const skill of match.missing) {
      missingCounts.set(skill, (missingCounts.get(skill) || 0) + 1);
    }
  }
  const topMissing = [...missingCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10);

  function addSkill(skill: string) {
    const next = new Set(userSkills);
    next.add(skill);
    setSkillsText([...next].join(", "));
  }

  return (
    <div className="space-y-4">
      <Panel>
        <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <label className="block">
            <span className="text-sm text-muted">Your skills</span>
            <input value={skillsText} onChange={(event) => setSkillsText(event.target.value)} placeholder="Python, SQL, Tableau" className="mt-1 h-11 w-full rounded-md border border-line bg-panel-strong px-3 text-foreground outline-none focus:border-accent" />
          </label>
          <div className="grid gap-3 sm:grid-cols-3">
            <Select label="Role" value={role} onChange={setRole} options={ROLE_CATEGORIES.filter((item) => item !== "Other")} />
            <Select label="Seniority" value={seniority} onChange={setSeniority} options={SENIORITY_LEVELS} />
            <Select label="Work mode" value={workMode} onChange={setWorkMode} options={WORK_MODES.filter((item) => item !== "Unknown")} />
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {skillOptions.slice(0, 18).map((skill) => (
            <button key={skill} onClick={() => addSkill(skill)} className="rounded-md border border-line px-2 py-1 text-xs text-muted hover:border-accent hover:text-foreground">
              {skill}
            </button>
          ))}
        </div>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Panel>
          <div className="mb-3 flex items-center gap-2">
            <Target size={18} className="text-accent" />
            <h2 className="text-lg font-semibold">Strong Matches ({strong.length})</h2>
          </div>
          {strong.length ? <MatchList rows={strong.slice(0, 40)} /> : <EmptyState>No strong matches yet. Add more skills or broaden filters.</EmptyState>}
        </Panel>
        <Panel>
          <h2 className="mb-3 text-lg font-semibold">Skills To Learn Next</h2>
          {topMissing.length ? (
            <div className="space-y-2">
              {topMissing.map(([skill, count], index) => (
                <div key={skill} className="flex items-center justify-between rounded-md border border-line bg-panel-strong px-3 py-2 text-sm">
                  <span>{index + 1}. {skill}</span>
                  <span className="text-muted">{count} matched jobs</span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState>Add skills to see gap recommendations.</EmptyState>
          )}
        </Panel>
      </div>

      <Panel>
        <h2 className="mb-3 text-lg font-semibold">Partial Matches ({partial.length})</h2>
        {partial.length ? <MatchList rows={partial.slice(0, 30)} compact /> : <EmptyState>No partial matches found.</EmptyState>}
      </Panel>
    </div>
  );
}

function MatchList({ rows, compact = false }: { rows: MatchRow[]; compact?: boolean }) {
  return (
    <div className="space-y-3">
      {rows.map((match) => {
        const sourceUrl = safeJobSourceUrl(match.listing.raw.source_url);

        return (
          <article key={match.listing.id || match.listing.raw.source_url} className="rounded-lg border border-line bg-panel-strong p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h3 className="font-semibold">{match.listing.raw.title || "Untitled role"}</h3>
                <div className="mt-1 text-sm text-muted">
                  {match.listing.raw.company || "Unknown"} · {compactSalary(match.listing.raw.salary_min, match.listing.raw.salary_max)} · {formatDate(match.listing.raw.posting_date)}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge>{Math.round(match.pct * 100)}% match</Badge>
                {sourceUrl && (
                  <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="text-accent">
                    <ExternalLink size={17} />
                  </a>
                )}
              </div>
            </div>
            {!compact && (
              <div className="mt-3 flex flex-wrap gap-2">
                {match.matched.map((skill) => <span key={skill} className="rounded-md bg-[#064e3b] px-2 py-1 text-xs text-emerald-100">{skill}</span>)}
                {match.missing.slice(0, 12).map((skill) => <span key={skill} className="rounded-md bg-[#4a1d23] px-2 py-1 text-xs text-rose-100">{skill}</span>)}
              </div>
            )}
          </article>
        );
      })}
    </div>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[] }) {
  return (
    <label className="block text-sm">
      <span className="text-muted">{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-11 w-full rounded-md border border-line bg-panel-strong px-3 text-foreground outline-none focus:border-accent">
        <option value="">Any</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}
