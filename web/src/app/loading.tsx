import {
  LoadingStatus,
  PanelSkeleton,
  Skeleton,
} from "@/components/loading-shell";

export default function Loading() {
  return (
    <div className="space-y-6" aria-label="Loading dashboard" aria-busy="true">
      <LoadingStatus>
        Crunching the latest Singapore data &amp; AI listings
      </LoadingStatus>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Skeleton className="mb-3 h-3 w-32" />
          <Skeleton className="h-9 w-80 max-w-full" />
        </div>
        <Skeleton className="h-10 w-44" />
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="rounded-lg border border-line bg-panel p-4">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="mt-3 h-8 w-24" />
            <Skeleton className="mt-3 h-3 w-36" />
          </div>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <PanelSkeleton tall />
        <PanelSkeleton tall />
      </div>

      <PanelSkeleton />
    </div>
  );
}
