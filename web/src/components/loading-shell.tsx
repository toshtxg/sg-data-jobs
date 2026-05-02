import { Sparkles } from "lucide-react";

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`shimmer rounded-md ${className}`} />;
}

export function LoadingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-hidden="true">
      <span className="loading-dot inline-block h-1.5 w-1.5 rounded-full bg-accent" />
      <span
        className="loading-dot inline-block h-1.5 w-1.5 rounded-full bg-accent"
        style={{ animationDelay: "0.15s" }}
      />
      <span
        className="loading-dot inline-block h-1.5 w-1.5 rounded-full bg-accent"
        style={{ animationDelay: "0.3s" }}
      />
    </span>
  );
}

export function LoadingStatus({ children }: { children: React.ReactNode }) {
  return (
    <div
      role="status"
      className="flex items-center gap-3 rounded-lg border border-line bg-panel px-4 py-3 text-sm text-muted"
    >
      <Sparkles size={16} className="text-accent" />
      <span className="text-foreground">{children}</span>
      <LoadingDots />
    </div>
  );
}

export function PanelSkeleton({ tall = false }: { tall?: boolean }) {
  return (
    <section className="rounded-lg border border-line bg-panel p-4">
      <Skeleton className="mb-4 h-5 w-44" />
      <Skeleton className={tall ? "h-72 w-full" : "h-40 w-full"} />
    </section>
  );
}
