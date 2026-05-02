import {
  LoadingStatus,
  Skeleton,
} from "@/components/loading-shell";

function JobCardSkeleton() {
  return (
    <article className="rounded-lg border border-line bg-panel p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <Skeleton className="h-5 w-2/3 max-w-md" />
          <Skeleton className="mt-2 h-3 w-1/2 max-w-xs" />
        </div>
        <Skeleton className="h-9 w-24 shrink-0" />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-6 w-20" />
        <Skeleton className="h-6 w-28" />
        <Skeleton className="h-6 w-32" />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Skeleton className="h-5 w-16" />
        <Skeleton className="h-5 w-20" />
        <Skeleton className="h-5 w-14" />
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-5 w-16" />
      </div>
    </article>
  );
}

export default function JobsLoading() {
  return (
    <div className="space-y-6" aria-label="Loading job explorer" aria-busy="true">
      <LoadingStatus>
        Loading {"≈"} thousands of classified Singapore listings
      </LoadingStatus>

      <div>
        <Skeleton className="mb-3 h-3 w-32" />
        <Skeleton className="h-9 w-72 max-w-full" />
      </div>

      <section className="rounded-lg border border-line bg-panel p-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index}>
              <Skeleton className="h-3 w-16" />
              <Skeleton className="mt-1 h-10 w-full" />
            </div>
          ))}
        </div>
        <Skeleton className="mt-4 h-3 w-3/4 max-w-xl" />
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <Skeleton className="h-4 w-64" />
          <Skeleton className="h-9 w-36" />
        </div>
      </section>

      <div className="grid gap-3">
        {Array.from({ length: 4 }).map((_, index) => (
          <JobCardSkeleton key={index} />
        ))}
      </div>
    </div>
  );
}
