import { Skeleton, SkeletonCard } from "@/components/ui";

/** The billing page while it loads: subscription and usage side by side, then the plans. */
export function BillingSkeleton() {
  return (
    <div aria-hidden className="space-y-8">
      <div className="grid gap-4 lg:grid-cols-2">
        <SkeletonCard lines={4} />
        <SkeletonCard lines={4} />
      </div>
      <div className="space-y-4">
        <Skeleton className="h-5 w-40" />
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }, (_, index) => (
            <div key={index} className="space-y-4 rounded-2xl border border-line bg-surface p-5">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-32" />
              <div className="space-y-2">
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-4/5" />
                <Skeleton className="h-3 w-3/5" />
              </div>
              <Skeleton className="h-9 w-full rounded-lg" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
