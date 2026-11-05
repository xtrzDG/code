import { Skeleton, SkeletonCard, SkeletonRows } from "@/components/ui";

const BUBBLES = ["w-2/5", "w-3/5", "w-1/3"] as const;

/** Chat bubbles, left and right, while a conversation loads. */
export function ChatBubblesSkeleton() {
  return (
    <div aria-hidden className="space-y-4">
      {BUBBLES.map((width, index) => (
        <div key={index} className={index % 2 === 1 ? "flex justify-end" : "flex"}>
          <Skeleton className={`h-11 rounded-2xl ${width}`} />
        </div>
      ))}
    </div>
  );
}

/** The test chat on its way: the version bar, the log and the message box. */
export function TestChatSkeleton() {
  return (
    <div aria-hidden className="overflow-hidden rounded-2xl border border-line bg-surface">
      <div className="flex items-center gap-3 border-b border-line px-4 py-3 sm:px-6">
        <Skeleton className="size-4 rounded-full" />
        <Skeleton className="h-3.5 w-56 max-w-full" />
      </div>
      <div className="h-[min(60vh,36rem)] min-h-72 px-4 py-5 sm:px-6">
        <ChatBubblesSkeleton />
      </div>
      <div className="flex gap-3 border-t border-line px-4 py-3 sm:px-6">
        <Skeleton className="h-10 flex-1 rounded-lg" />
        <Skeleton className="size-10 rounded-lg" />
      </div>
    </div>
  );
}

/** The version list on its way. */
export function VersionsSkeleton() {
  return <SkeletonRows rows={4} />;
}

/** One version on its way: its header card, the checklist and the panels. */
export function VersionDetailSkeleton() {
  return (
    <div aria-hidden className="space-y-6">
      <SkeletonCard lines={2} />
      <div className="grid gap-6 lg:grid-cols-2">
        <SkeletonCard lines={5} />
        <SkeletonCard lines={5} />
      </div>
    </div>
  );
}
