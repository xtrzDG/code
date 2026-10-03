import { Skeleton, SkeletonCard } from "@/components/ui";

/** The wizard while it loads: the six steps on the side and a step's form. */
export function WizardSkeleton() {
  return (
    <div aria-hidden className="grid gap-6 lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-8">
      <div className="space-y-4">
        <div className="space-y-1 rounded-2xl border border-line bg-surface p-2">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={index} className="flex items-center gap-3 rounded-lg px-2.5 py-2">
              <Skeleton className="size-6 shrink-0 rounded-full" />
              <Skeleton className={index % 2 === 0 ? "h-3.5 w-32" : "h-3.5 w-24"} />
            </div>
          ))}
        </div>
        <SkeletonCard lines={2} header={false} />
      </div>
      <div className="space-y-4 rounded-2xl border border-line bg-surface p-5 sm:p-6">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-3.5 w-3/4" />
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="space-y-2 pt-2">
            <Skeleton className="h-3.5 w-28" />
            <Skeleton className="h-9 w-full rounded-lg" />
          </div>
        ))}
        <div className="flex justify-end gap-3 pt-2">
          <Skeleton className="h-9 w-24 rounded-lg" />
          <Skeleton className="h-9 w-32 rounded-lg" />
        </div>
      </div>
    </div>
  );
}
