import { Skeleton, SkeletonCard } from "@/components/ui";

/** One KPI tile: a label, a big number and a hint, sized like StatTile. */
function KpiTileSkeleton({ hint }: { hint: boolean }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 sm:p-5">
      <Skeleton className="h-3.5 w-24" />
      <Skeleton className="mt-2.5 h-7 w-16 sm:h-8" />
      {hint ? <Skeleton className="mt-2 h-3 w-32 max-w-full" /> : null}
    </div>
  );
}

/** The period's numbers while they load: the range, six KPI tiles, the trend and the package. */
export function DashboardPeriodSkeleton() {
  return (
    <div aria-hidden className="space-y-4">
      <Skeleton className="h-3.5 w-48" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {Array.from({ length: 6 }, (_, index) => (
          <KpiTileSkeleton key={index} hint={index === 0 || index === 3} />
        ))}
      </div>
      <div className="rounded-2xl border border-line bg-surface p-5">
        <Skeleton className="h-4 w-36" />
        <div className="mt-5 flex h-36 items-end gap-2">
          {[40, 65, 30, 80, 55, 90, 45, 70, 35, 60, 75, 50].map((height, index) => (
            <Skeleton key={index} className="flex-1 rounded-sm" style={{ height: `${height}%` }} />
          ))}
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <SkeletonCard lines={3} />
        <SkeletonCard lines={3} className="lg:col-span-2" />
      </div>
    </div>
  );
}

/** The whole dashboard on its way: the next step, two attention tiles and the period. */
export function DashboardSkeleton() {
  return (
    <div aria-hidden className="space-y-6">
      <div className="rounded-2xl border border-line bg-surface p-5">
        <div className="flex flex-wrap items-center gap-3">
          <Skeleton className="h-5 w-24 rounded-full" />
          <Skeleton className="h-4 w-56 max-w-full" />
        </div>
        <Skeleton className="mt-3 h-3.5 w-3/4" />
        <Skeleton className="mt-4 h-9 w-36 rounded-lg" />
      </div>
      <div className="space-y-3">
        <Skeleton className="h-3.5 w-36" />
        <div className="grid gap-3 sm:grid-cols-2">
          {Array.from({ length: 2 }, (_, index) => (
            <div key={index} className="flex items-center gap-4 rounded-2xl border border-line bg-surface p-4">
              <Skeleton className="size-10 shrink-0 rounded-xl" />
              <div className="min-w-0 flex-1 space-y-2">
                <Skeleton className="h-3.5 w-32" />
                <Skeleton className="h-3 w-48 max-w-full" />
              </div>
              <Skeleton className="h-7 w-8" />
            </div>
          ))}
        </div>
      </div>
      <DashboardPeriodSkeleton />
    </div>
  );
}
