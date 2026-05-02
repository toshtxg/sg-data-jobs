import { compactListingsForClient, loadClassifiedListings } from "@/lib/data";
import { CompanyLeaderboard } from "@/components/company-leaderboard";
import { PageHeader } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function CompaniesPage() {
  const listings = compactListingsForClient(await loadClassifiedListings());
  return (
    <>
      <PageHeader title="Companies" eyebrow="Who's hiring and how often" />
      <CompanyLeaderboard listings={listings} />
    </>
  );
}
