import { Skeleton, SkeletonCard, SkeletonRows } from "@/components/ui";

/** The client list while it loads: the summary tiles, the filters and rows of clients. */
export function AdminClientsSkeleton() {
  return (
    <div aria-hidden className="space-y-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 5 }, (_, index) => (
          <div key={index} className="rounded-2xl border border-line bg-surface p-4">
            <Skeleton className="h-3.5 w-20" />
            <Skeleton className="mt-2.5 h-7 w-12" />
          </div>
        ))}
      </div>
      <div className="rounded-2xl border border-line bg-surface">
        <div className="flex flex-wrap gap-3 border-b border-line p-5">
          <Skeleton className="h-9 w-full max-w-xs rounded-lg" />
          <Skeleton className="h-9 w-32 rounded-lg" />
          <Skeleton className="h-9 w-32 rounded-lg" />
        </div>
        <div className="p-5">
          <SkeletonRows rows={5} />
        </div>
      </div>
    </div>
  );
}

/** One client while it loads: the header card and the cards of its numbers. */
export function AdminClientSkeleton() {
  return (
    <div aria-hidden className="space-y-6">
      <SkeletonCard lines={2} />
      <div className="grid gap-4 lg:grid-cols-2">
        <SkeletonCard lines={4} />
        <SkeletonCard lines={4} />
        <SkeletonCard lines={3} />
        <SkeletonCard lines={3} />
      </div>
    </div>
  );
}
