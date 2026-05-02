import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { unstable_cache } from "next/cache";
import type { ClassifiedListing, MarketSnapshot, RawListing } from "@/lib/types";

type SupabaseClassifiedRow = Omit<ClassifiedListing, "raw">;
type SupabaseRawRow = RawListing & { id: string };

let client: SupabaseClient | null = null;

function getSupabaseClient() {
  if (client) return client;
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_KEY;
  if (!url || !key) {
    throw new Error("Missing SUPABASE_URL or SUPABASE_KEY.");
  }
  client = createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  return client;
}

type LoadListingOptions = {
  limit?: number;
  includeDescription?: boolean;
};

function emptyRawListing(): RawListing {
  return {
    title: null,
    company: null,
    description: null,
    salary_min: null,
    salary_max: null,
    salary_currency: "SGD",
    source_url: null,
    posting_date: null,
    source: null,
    scraped_at: null,
  };
}

function normalizeClassifiedRow(
  row: SupabaseClassifiedRow,
  rawValue: RawListing | null | undefined,
  includeDescription: boolean,
): ClassifiedListing {
  const normalized: ClassifiedListing = {
    id: row.id,
    listing_id: row.listing_id,
    role_category: row.role_category,
    seniority_level: row.seniority_level,
    technical_skills: row.technical_skills || [],
    soft_skills: row.soft_skills || [],
    domain_knowledge: row.domain_knowledge || [],
    requires_ai_ml: row.requires_ai_ml,
    remote_hybrid_onsite: row.remote_hybrid_onsite,
    industry: row.industry,
    classified_at: row.classified_at,
    model_used: row.model_used,
    raw: { ...emptyRawListing(), ...(rawValue || {}) },
  };

  if (!includeDescription) {
    normalized.raw.description = null;
  } else if (normalized.raw.description) {
    normalized.raw.description = normalized.raw.description.slice(0, 900);
  }

  return normalized;
}

async function fetchClassifiedRows(supabase: SupabaseClient, limit?: number) {
  const pageSize = 1000;
  let offset = 0;
  const rows: SupabaseClassifiedRow[] = [];

  while (true) {
    const nextPageSize = limit ? Math.min(pageSize, limit - rows.length) : pageSize;
    if (nextPageSize <= 0) break;

    const { data, error } = await supabase
      .from("classified_listings")
      .select(
        "id,listing_id,role_category,seniority_level,technical_skills,soft_skills,domain_knowledge,requires_ai_ml,remote_hybrid_onsite,industry,classified_at,model_used",
      )
      .order("classified_at", { ascending: false })
      .range(offset, offset + nextPageSize - 1);

    if (error) throw new Error(error.message);
    rows.push(...((data || []) as SupabaseClassifiedRow[]));
    if (!data || data.length < nextPageSize) break;
    offset += data.length;
  }

  return rows;
}

async function fetchRawListings(
  supabase: SupabaseClient,
  listingIds: string[],
  includeDescription: boolean,
) {
  const rawFields = includeDescription
    ? "id,title,company,description,salary_min,salary_max,salary_currency,source_url,posting_date,scraped_at"
    : "id,title,company,salary_min,salary_max,salary_currency,source_url,posting_date,scraped_at";
  const rawById = new Map<string, RawListing>();

  if (listingIds.length > 1000) {
    const wantedIds = new Set(listingIds);
    const pageSize = includeDescription ? 500 : 1000;

    for (let offset = 0; ; offset += pageSize) {
      const { data, error } = await supabase
        .from("raw_listings")
        .select(rawFields)
        .range(offset, offset + pageSize - 1);

      if (error) throw new Error(error.message);
      for (const raw of (data || []) as unknown as SupabaseRawRow[]) {
        if (wantedIds.has(raw.id)) rawById.set(raw.id, raw);
      }
      if (!data || data.length < pageSize || rawById.size >= wantedIds.size) break;
    }

    return rawById;
  }

  const chunkSize = includeDescription ? 40 : 80;

  for (let index = 0; index < listingIds.length; index += chunkSize) {
    const chunk = listingIds.slice(index, index + chunkSize);
    const { data, error } = await supabase
      .from("raw_listings")
      .select(rawFields)
      .in("id", chunk);

    if (error) throw new Error(error.message);
    for (const raw of (data || []) as unknown as SupabaseRawRow[]) {
      rawById.set(raw.id, raw);
    }
  }

  return rawById;
}

async function loadClassifiedListingsUncached(
  includeDescription: boolean,
  limit: number | null,
) {
  const supabase = getSupabaseClient();
  const classifiedRows = await fetchClassifiedRows(supabase, limit ?? undefined);
  const listingIds = [
    ...new Set(classifiedRows.map((row) => row.listing_id).filter(Boolean) as string[]),
  ];
  const rawById = await fetchRawListings(supabase, listingIds, includeDescription);

  return classifiedRows.map((row) =>
    normalizeClassifiedRow(
      row,
      row.listing_id ? rawById.get(row.listing_id) : null,
      includeDescription,
    ),
  );
}

const loadClassifiedListingsCached = unstable_cache(
  loadClassifiedListingsUncached,
  ["classified-listings"],
  { revalidate: 900 },
);

export function loadClassifiedListings(options: LoadListingOptions = {}) {
  return loadClassifiedListingsCached(
    Boolean(options.includeDescription),
    options.limit ?? null,
  );
}

async function loadSnapshotsUncached() {
  const supabase = getSupabaseClient();
  const { data, error } = await supabase
    .from("market_snapshots")
    .select("*")
    .order("snapshot_date", { ascending: true });
  if (error) throw new Error(error.message);
  return (data || []) as MarketSnapshot[];
}

export const loadSnapshots = unstable_cache(loadSnapshotsUncached, ["market-snapshots"], {
  revalidate: 900,
});

async function loadLatestPullTimestampUncached() {
  const supabase = getSupabaseClient();
  const { data, error } = await supabase
    .from("raw_listings")
    .select("scraped_at")
    .order("scraped_at", { ascending: false })
    .limit(1);
  if (error) throw new Error(error.message);
  return data?.[0]?.scraped_at as string | null | undefined;
}

export const loadLatestPullTimestamp = unstable_cache(
  loadLatestPullTimestampUncached,
  ["latest-pull-timestamp"],
  { revalidate: 900 },
);

export function compactListingsForClient(
  listings: ClassifiedListing[],
  options: { includeDescription?: boolean } = {},
) {
  return listings.map((row) => ({
    id: row.id,
    role_category: row.role_category,
    seniority_level: row.seniority_level,
    technical_skills: row.technical_skills || [],
    requires_ai_ml: row.requires_ai_ml,
    remote_hybrid_onsite: row.remote_hybrid_onsite,
    industry: row.industry,
    raw: {
      title: row.raw.title,
      company: row.raw.company,
      description: options.includeDescription ? row.raw.description : null,
      salary_min: row.raw.salary_min,
      salary_max: row.raw.salary_max,
      source_url: row.raw.source_url,
      posting_date: row.raw.posting_date,
    },
  })) satisfies ClassifiedListing[];
}

export async function generateMarketSummary(snapshot: MarketSnapshot | null) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey || !snapshot) return null;
  const model = process.env.OPENAI_SUMMARY_MODEL || "gpt-5-nano";
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 3_500);

  try {
    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages: [
          {
            role: "system",
            content:
              "You are a Singapore tech job market analyst. Write clear, data-driven market briefings.",
          },
          {
            role: "user",
            content: `Write a concise 3 paragraph market briefing from this snapshot. Use specific numbers.\n\n${JSON.stringify(
              {
                total_listings: snapshot.total_listings,
                new_this_week: snapshot.new_listings_count,
                listings_by_role: snapshot.listings_by_role,
                listings_by_seniority: snapshot.listings_by_seniority,
                top_skills: snapshot.top_skills?.slice(0, 15),
                avg_salary_by_role: snapshot.avg_salary_by_role,
                snapshot_date: snapshot.snapshot_date,
              },
            )}`,
          },
        ],
      }),
      next: { revalidate: 3600 },
      signal: controller.signal,
    });
    if (!response.ok) return null;
    const payload = (await response.json()) as {
      choices?: { message?: { content?: string } }[];
    };
    return payload.choices?.[0]?.message?.content || null;
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}
