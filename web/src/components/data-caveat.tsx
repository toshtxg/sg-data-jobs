import { Info } from "lucide-react";

export function DataCaveat() {
  return (
    <div className="mb-6 flex items-start gap-3 rounded-lg border border-line bg-panel p-4 text-sm text-muted">
      <Info size={18} className="mt-0.5 shrink-0 text-accent" />
      <div>
        <span className="text-foreground">About the data.</span> Listings come
        from{" "}
        <a
          href="https://www.mycareersfuture.gov.sg/"
          target="_blank"
          rel="noreferrer"
          className="text-accent hover:underline"
        >
          MyCareersFuture.gov.sg
        </a>
        , Singapore's government-mandated job portal. Under the Fair
        Consideration Framework, employers must post here for at least 14 days
        before applying for an Employment Pass or S Pass. This dataset is
        therefore a slice of the SG market — skewed toward roles where
        employers are open to hiring foreign talent — not a complete picture.
      </div>
    </div>
  );
}
