"use client";

import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import {
  Check,
  ChevronDown,
  Download,
  ExternalLink,
  Filter,
} from "lucide-react";
import {
  AI_INVOLVEMENT_LEVELS,
  ROLE_CATEGORIES,
  SENIORITY_LEVELS,
} from "@/lib/constants";
import {
  analyzeAiCategories,
  classifyAiInvolvement,
  formatDate,
  formatSalary,
  toNumber,
} from "@/lib/market";
import { csvCell, safeJobSourceUrl } from "@/lib/security";
import type { ClassifiedListing } from "@/lib/types";
import { Badge, EmptyState, Panel } from "@/components/ui";

type SearchQuery = {
  phrase: string;
  terms: string[];
  pairs: string[];
};

type SearchScore = {
  score: number;
  matchedTerms: number;
};

const SORT_LABELS: Record<string, string> = {
  newest: "newest postings",
  salary: "highest salary",
  role: "role name",
  company: "company name",
};

function normalizeSearchText(value: string | null | undefined) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function buildSearchQuery(value: string): SearchQuery {
  const phrase = normalizeSearchText(value);
  const terms = [...new Set(phrase.split(/\s+/).filter(Boolean))];
  const pairs =
    terms.length > 1
      ? terms.slice(0, -1).map((_, index) => terms.slice(index, index + 2).join(" "))
      : [];

  return { phrase, terms, pairs };
}

function countFieldMatches(text: string, terms: string[]) {
  if (!text || !terms.length) return { exact: 0, partial: 0 };

  const words = new Set(text.split(/\s+/).filter(Boolean));
  let exact = 0;
  let partial = 0;

  for (const term of terms) {
    if (words.has(term)) {
      exact += 1;
      continue;
    }

    if (term.length >= 3 && text.includes(term)) {
      partial += 1;
    }
  }

  return { exact, partial };
}

function scoreSearch(row: ClassifiedListing, query: SearchQuery): SearchScore {
  if (!query.terms.length) return { score: 0, matchedTerms: 0 };

  const title = normalizeSearchText(row.raw.title);
  const role = normalizeSearchText(row.role_category);
  const company = normalizeSearchText(row.raw.company);
  const seniority = normalizeSearchText(row.seniority_level);
  const industry = normalizeSearchText(row.industry);
  const workMode = normalizeSearchText(row.remote_hybrid_onsite);
  const skills = (row.technical_skills || []).map((skill) => normalizeSearchText(skill));
  const skillsText = skills.filter(Boolean).join(" ");
  const metaText = [company, seniority, industry, workMode].filter(Boolean).join(" ");
  const combinedText = [title, role, skillsText, metaText].filter(Boolean).join(" ");

  const titleMatches = countFieldMatches(title, query.terms);
  const roleMatches = countFieldMatches(role, query.terms);
  const skillMatches = countFieldMatches(skillsText, query.terms);
  const metaMatches = countFieldMatches(metaText, query.terms);

  let score = 0;

  if (query.phrase) {
    if (title === query.phrase) score += 500;
    else if (title.includes(query.phrase)) score += 360;

    if (role === query.phrase) score += 320;
    else if (role.includes(query.phrase)) score += 220;

    if (skills.some((skill) => skill === query.phrase)) score += 260;
    else if (skillsText.includes(query.phrase)) score += 180;

    if (company === query.phrase) score += 140;
    else if (company.includes(query.phrase)) score += 90;
  }

  score += titleMatches.exact * 90 + titleMatches.partial * 35;
  score += roleMatches.exact * 70 + roleMatches.partial * 28;
  score += skillMatches.exact * 55 + skillMatches.partial * 22;
  score += metaMatches.exact * 26 + metaMatches.partial * 12;

  for (const pair of query.pairs) {
    if (title.includes(pair)) score += 70;
    else if (role.includes(pair)) score += 50;
    else if (skillsText.includes(pair)) score += 34;
  }

  const matchedTerms = query.terms.filter((term) => combinedText.includes(term)).length;
  const allTermsInTitle = query.terms.every((term) => title.includes(term));
  const allTermsInCoreFields = query.terms.every((term) =>
    `${title} ${role} ${skillsText}`.includes(term),
  );

  if (allTermsInTitle) score += 220;
  if (!allTermsInTitle && allTermsInCoreFields) score += 150;
  if (matchedTerms === query.terms.length) score += 90;
  score += matchedTerms * 18;
  score -= Math.max(query.terms.length - matchedTerms, 0) * 12;

  return matchedTerms ? { score, matchedTerms } : { score: 0, matchedTerms: 0 };
}

function compareListings(a: ClassifiedListing, b: ClassifiedListing, sort: string) {
  if (sort === "salary") {
    return (toNumber(b.raw.salary_max) || 0) - (toNumber(a.raw.salary_max) || 0);
  }

  if (sort === "company") {
    return String(a.raw.company).localeCompare(String(b.raw.company));
  }

  if (sort === "role") {
    return String(a.role_category).localeCompare(String(b.role_category));
  }

  return String(b.raw.posting_date).localeCompare(String(a.raw.posting_date));
}

export function JobExplorer({ listings }: { listings: ClassifiedListing[] }) {
  const [roles, setRoles] = useState<string[]>([]);
  const [seniorityLevels, setSeniorityLevels] = useState<string[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [aiLevels, setAiLevels] = useState<string[]>([]);
  const [salaryMin, setSalaryMin] = useState("");
  const [sort, setSort] = useState("newest");
  const deferredSearchInput = useDeferredValue(searchInput);
  const searchQuery = useMemo(
    () => buildSearchQuery(deferredSearchInput),
    [deferredSearchInput],
  );

  const filtered = useMemo(() => {
    const min = Number(salaryMin || 0);
    const hasSearch = searchQuery.terms.length > 0;

    return listings
      .filter((row) => (roles.length ? roles.includes(row.role_category || "") : true))
      .filter((row) =>
        seniorityLevels.length ? seniorityLevels.includes(row.seniority_level || "") : true,
      )
      .filter((row) => {
        if (!min) return true;
        const postedMax = toNumber(row.raw.salary_max);
        return postedMax === null || postedMax >= min;
      })
      .filter((row) => {
        if (!aiLevels.length) return true;
        const involvement = classifyAiInvolvement(analyzeAiCategories(row));
        return aiLevels.some((level) => involvement.includes(level));
      })
      .map((row) => ({
        row,
        search: hasSearch ? scoreSearch(row, searchQuery) : { score: 0, matchedTerms: 0 },
      }))
      .filter(({ search }) => (hasSearch ? search.score > 0 : true))
      .sort((a, b) => {
        if (hasSearch && b.search.score !== a.search.score) {
          return b.search.score - a.search.score;
        }

        if (hasSearch && b.search.matchedTerms !== a.search.matchedTerms) {
          return b.search.matchedTerms - a.search.matchedTerms;
        }

        return compareListings(a.row, b.row, sort);
      })
      .map(({ row }) => row);
  }, [aiLevels, listings, roles, salaryMin, searchQuery, seniorityLevels, sort]);

  function downloadCsv() {
    const rows = filtered.map((row) => ({
      Title: row.raw.title || "",
      Company: row.raw.company || "",
      Role: row.role_category || "",
      Seniority: row.seniority_level || "",
      SalaryMin: row.raw.salary_min || "",
      SalaryMax: row.raw.salary_max || "",
      Skills: (row.technical_skills || []).join(", "),
      Industry: row.industry || "",
      WorkMode: row.remote_hybrid_onsite || "",
      Posted: row.raw.posting_date || "",
      Url: safeJobSourceUrl(row.raw.source_url) || "",
    }));
    const header = Object.keys(rows[0] || { Title: "" });
    const csv = [
      header.join(","),
      ...rows.map((row) =>
        header
          .map((key) => csvCell(row[key as keyof typeof row]))
          .join(","),
      ),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "sg-data-jobs.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <Panel>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
          <MultiSelect
            label="Role"
            options={ROLE_CATEGORIES}
            values={roles}
            onChange={setRoles}
            anyLabel="Any"
          />
          <MultiSelect
            label="Seniority"
            options={SENIORITY_LEVELS}
            values={seniorityLevels}
            onChange={setSeniorityLevels}
            anyLabel="Any"
          />
          <MultiSelect
            label="AI level"
            options={Object.keys(AI_INVOLVEMENT_LEVELS)}
            values={aiLevels}
            onChange={setAiLevels}
            anyLabel="Any"
          />
          <Select
            label="Sort"
            value={sort}
            onChange={setSort}
            options={["newest", "salary", "role", "company"]}
            includeAny={false}
          />
          <label className="block text-sm">
            <span className="text-muted">Min salary</span>
            <input
              value={salaryMin}
              onChange={(event) => setSalaryMin(event.target.value)}
              inputMode="numeric"
              placeholder="e.g. 8000"
              className="mt-1 h-10 w-full rounded-md border border-line bg-panel-strong px-3 text-foreground outline-none focus:border-accent"
            />
          </label>
          <label className="block text-sm">
            <span className="text-muted">Search</span>
            <input
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search titles, skills, or companies"
              className="mt-1 h-10 w-full rounded-md border border-line bg-panel-strong px-3 text-foreground outline-none focus:border-accent"
            />
          </label>
        </div>
        <div className="mt-3 text-xs text-muted">
          Search checks title, role, company, skills, and job metadata. Exact title phrases and
          listings matching more of your terms are ranked first. Try queries like{" "}
          <span className="text-foreground">technical program manager</span>,{" "}
          <span className="text-foreground">Python</span>, or{" "}
          <span className="text-foreground">OpenAI</span>.
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
          <div className="flex items-center gap-2">
            <Filter size={16} />
            {filtered.length.toLocaleString()} jobs found from {listings.length.toLocaleString()}{" "}
            classified listings
            {searchQuery.terms.length > 0
              ? `. Ranked by relevance, then ${SORT_LABELS[sort] || sort}.`
              : "."}
          </div>
          <button
            onClick={downloadCsv}
            className="inline-flex h-9 items-center gap-2 rounded-md border border-line bg-panel-strong px-3 text-foreground hover:border-accent"
          >
            <Download size={16} />
            Download CSV
          </button>
        </div>
      </Panel>

      {filtered.length ? (
        <div className="grid gap-3">
          {filtered.slice(0, 100).map((row) => {
            const sourceUrl = safeJobSourceUrl(row.raw.source_url);

            return (
              <article
                key={row.id || row.raw.source_url}
                className="rounded-lg border border-line bg-panel p-4"
              >
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">
                      {row.raw.title || "Untitled role"}
                    </h2>
                    <div className="mt-1 text-sm text-muted">
                      {row.raw.company || "Unknown company"} · {formatDate(row.raw.posting_date)} ·{" "}
                      {row.remote_hybrid_onsite || "Unknown"}
                    </div>
                  </div>
                  {sourceUrl && (
                    <a
                      href={sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex h-9 shrink-0 items-center justify-center gap-2 rounded-md bg-accent px-3 text-sm font-semibold text-[#07110f]"
                    >
                      Apply <ExternalLink size={15} />
                    </a>
                  )}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Badge>{row.role_category || "Unknown role"}</Badge>
                  <Badge>{row.seniority_level || "Unknown seniority"}</Badge>
                  <Badge>{row.industry || "Unknown industry"}</Badge>
                  <Badge>{formatSalary(row.raw.salary_min, row.raw.salary_max)}</Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {(row.technical_skills || []).slice(0, 18).map((skill) => (
                    <span
                      key={skill}
                      className="rounded-md bg-[#252a32] px-2 py-1 text-xs text-muted"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
                {row.raw.description && (
                  <p className="mt-3 line-clamp-3 text-sm leading-6 text-muted">
                    {row.raw.description.slice(0, 700)}
                  </p>
                )}
              </article>
            );
          })}
        </div>
      ) : (
        <EmptyState>No jobs match the current filters or search.</EmptyState>
      )}
      {filtered.length > 100 && (
        <div className="rounded-lg border border-line bg-panel p-3 text-sm text-muted">
          Showing first 100 results. Narrow filters to inspect the rest.
        </div>
      )}
    </div>
  );
}

function MultiSelect({
  label,
  options,
  values,
  onChange,
  anyLabel,
}: {
  label: string;
  options: string[];
  values: string[];
  onChange: (values: string[]) => void;
  anyLabel: string;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function handlePointer(event: PointerEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("pointerdown", handlePointer);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("pointerdown", handlePointer);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  function toggleValue(option: string) {
    onChange(
      values.includes(option)
        ? values.filter((value) => value !== option)
        : [...values, option],
    );
  }

  const summary = values.length ? values.join(", ") : anyLabel;

  return (
    <div ref={containerRef} className="relative block text-sm">
      <span className="text-muted">{label}</span>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className={`mt-1 flex h-10 w-full items-center justify-between rounded-md border px-3 text-left text-foreground outline-none transition ${
          open ? "border-accent bg-[#262b33]" : "border-line bg-panel-strong"
        }`}
      >
        <span className="truncate">{summary}</span>
        <ChevronDown
          size={16}
          className={`shrink-0 text-muted transition ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-30 mt-2 w-full rounded-md border border-line bg-panel p-2 shadow-[0_14px_32px_rgba(0,0,0,0.35)]">
          <button
            type="button"
            onClick={() => onChange([])}
            className={`flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition ${
              values.length === 0
                ? "bg-panel-strong text-foreground"
                : "text-muted hover:bg-panel-strong hover:text-foreground"
            }`}
          >
            <span>{anyLabel}</span>
            {values.length === 0 && <Check size={16} className="text-accent" />}
          </button>
          <div className="mt-2 max-h-60 space-y-1 overflow-y-auto">
            {options.map((option) => {
              const selected = values.includes(option);
              return (
                <label
                  key={option}
                  className={`flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm transition ${
                    selected
                      ? "bg-panel-strong text-foreground"
                      : "text-muted hover:bg-panel-strong hover:text-foreground"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => toggleValue(option)}
                    className="h-4 w-4 rounded border-line bg-panel-strong accent-[var(--accent)]"
                  />
                  <span className="min-w-0 flex-1">{option}</span>
                </label>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
  includeAny = true,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  includeAny?: boolean;
}) {
  return (
    <label className="block text-sm">
      <span className="text-muted">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 h-10 w-full rounded-md border border-line bg-panel-strong px-3 text-foreground outline-none focus:border-accent"
      >
        {includeAny && <option value="">Any</option>}
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}
