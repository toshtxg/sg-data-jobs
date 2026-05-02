import {
  LoadingStatus,
  PanelSkeleton,
  Skeleton,
} from "@/components/loading-shell";

export default function CompaniesLoading() {
  return (
    <div className="space-y-6" aria-label="Loading company leaderboard" aria-busy="true">
      <LoadingStatus>Mapping who&apos;s hiring across Singapore</LoadingStatus>

      <div>
        <Skeleton className="mb-3 h-3 w-32" />
        <Skeleton className="h-9 w-64 max-w-full" />
      </div>

      <section className="rounded-lg border border-line bg-panel p-4">
        <Skeleton className="mb-4 h-5 w-44" />
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, index) => (
            <div
              key={index}
              className="flex items-center gap-3 rounded-md border border-line bg-panel-strong px-3 py-2"
            >
              <Skeleton className="h-4 w-6" />
              <Skeleton className="h-4 flex-1 max-w-xs" />
              <Skeleton className="h-4 w-12" />
            </div>
          ))}
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-2">
        <PanelSkeleton tall />
        <PanelSkeleton tall />
      </div>

      <PanelSkeleton />
    </div>
  );
}
