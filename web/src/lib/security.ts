const SAFE_JOB_SOURCE_HOSTS = new Set([
  "mycareersfuture.gov.sg",
  "www.mycareersfuture.gov.sg",
]);
const CSV_FORMULA_PREFIX = /^[=+\-@\t\r]/;

export function safeJobSourceUrl(value: string | null | undefined) {
  if (!value) return null;

  try {
    const url = new URL(value);
    if (url.protocol !== "https:") return null;
    if (!SAFE_JOB_SOURCE_HOSTS.has(url.hostname.toLowerCase())) return null;
    return url.toString();
  } catch {
    return null;
  }
}

export function csvCell(value: unknown) {
  const raw = String(value ?? "");
  const safe = CSV_FORMULA_PREFIX.test(raw) ? `'${raw}` : raw;
  return `"${safe.replaceAll('"', '""')}"`;
}
