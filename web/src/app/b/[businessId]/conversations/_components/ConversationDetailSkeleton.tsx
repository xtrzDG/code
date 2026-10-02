import { LoadingRegion, Skeleton } from "@/components/ui";

const BUBBLES = [
  { side: "start", width: "w-3/5" },
  { side: "end", width: "w-1/2" },
  { side: "start", width: "w-2/5" },
  { side: "end", width: "w-3/5" },
] as const;

/** The conversation card while it loads: the customer header and a transcript of bubbles. */
export function ConversationDetailSkeleton({ label }: { label: string }) {
  return (
    <LoadingRegion label={label} className="space-y-4">
      <div aria-hidden className="rounded-2xl border border-line bg-surface p-5">
        <div className="flex items-start gap-4">
          <Skeleton className="size-12 shrink-0 rounded-full" />
          <div className="min-w-0 flex-1 space-y-2.5">
            <div className="flex flex-wrap items-center gap-2">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-5 w-16 rounded-full" />
            </div>
            <Skeleton className="h-3.5 w-56 max-w-full" />
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-line pt-4 sm:grid-cols-4">
          {Array.from({ length: 4 }, (_, index) => (
            <div key={index} className="space-y-1.5">
              <Skeleton className="h-3 w-16" />
              <Skeleton className="h-3.5 w-24" />
            </div>
          ))}
        </div>
      </div>
      <div aria-hidden className="rounded-2xl border border-line bg-surface">
        <div className="border-b border-line px-5 py-4">
          <Skeleton className="h-4 w-28" />
        </div>
        <div className="space-y-3 p-5">
          {BUBBLES.map((bubble, index) => (
            <div key={index} className={bubble.side === "end" ? "flex justify-end" : "flex"}>
              <Skeleton className={`h-12 rounded-2xl ${bubble.width}`} />
            </div>
          ))}
        </div>
      </div>
    </LoadingRegion>
  );
}
