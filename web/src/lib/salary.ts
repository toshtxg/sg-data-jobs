export type SalaryBin = {
  label: string;
  min: number;
  max: number;
};

export const SALARY_BINS: SalaryBin[] = [
  { label: "Under $5k", min: 0, max: 5000 },
  { label: "$5k–$7k", min: 5000, max: 7000 },
  { label: "$7k–$10k", min: 7000, max: 10000 },
  { label: "$10k–$15k", min: 10000, max: 15000 },
  { label: "$15k–$20k", min: 15000, max: 20000 },
  { label: "$20k+", min: 20000, max: Number.POSITIVE_INFINITY },
];

function toNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined) return null;
  const num = typeof value === "number" ? value : Number(value);
  return Number.isFinite(num) ? num : null;
}

export function assignSalaryBin(
  salaryMin: number | string | null | undefined,
  salaryMax: number | string | null | undefined,
): string | null {
  const values = [toNumber(salaryMin), toNumber(salaryMax)].filter(
    (v): v is number => v !== null,
  );
  if (values.length === 0) return null;
  const midpoint = values.reduce((acc, v) => acc + v, 0) / values.length;
  const bin = SALARY_BINS.find((b) => midpoint >= b.min && midpoint < b.max);
  return bin ? bin.label : null;
}

export function formatSalaryRange(
  salaryMin: number | string | null | undefined,
  salaryMax: number | string | null | undefined,
): string {
  const lo = toNumber(salaryMin);
  const hi = toNumber(salaryMax);
  const fmt = (v: number) => `$${Math.round(v).toLocaleString()}`;
  if (lo !== null && hi !== null) return `${fmt(lo)}–${fmt(hi)}`;
  if (hi !== null) return `Up to ${fmt(hi)}`;
  if (lo !== null) return `From ${fmt(lo)}`;
  return "—";
}
