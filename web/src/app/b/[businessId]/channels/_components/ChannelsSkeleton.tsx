import { Skeleton, SkeletonCard } from "@/components/ui";

/** One channel card: the icon tile, the name with its state and a line about it, and the action. */
function ChannelCardSkeleton() {
  return (
    <div className="flex h-full flex-col rounded-2xl border border-line bg-surface p-5">
      <div className="flex items-start gap-3">
        <Skeleton className="size-10 shrink-0 rounded-xl" />
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-3/5" />
        </div>
      </div>
      <Skeleton className="mt-5 h-8 w-28 rounded-lg" />
    </div>
  );
}

/** The channels page while it loads: the customer channel cards, then the tools. */
export function ChannelsSkeleton() {
  return (
    <div aria-hidden className="space-y-8">
      <div className="space-y-4">
        <div className="space-y-2">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-3.5 w-72 max-w-full" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {Array.from({ length: 6 }, (_, index) => (
            <ChannelCardSkeleton key={index} />
          ))}
        </div>
      </div>
      <div className="space-y-4">
        <Skeleton className="h-5 w-40" />
        <div className="grid gap-4 xl:grid-cols-2">
          <SkeletonCard lines={2} />
          <SkeletonCard lines={2} />
        </div>
      </div>
    </div>
  );
}
