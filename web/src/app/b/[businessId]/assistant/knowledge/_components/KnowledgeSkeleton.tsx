import { Skeleton } from "@/components/ui";

/** Items of a kind while they load: a group heading and rows with a switch and actions. */
export function KnowledgeRowsSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div aria-hidden>
      <div className="bg-surface-muted/60 px-4 py-2.5 sm:px-6">
        <Skeleton className="h-3 w-24" />
      </div>
      <div className="divide-y divide-line">
        {Array.from({ length: rows }, (_, index) => (
          <div key={index} className="flex items-center gap-4 px-4 py-3.5 sm:px-6">
            <div className="min-w-0 flex-1 space-y-2">
              <Skeleton className={index % 2 === 0 ? "h-3.5 w-48 max-w-full" : "h-3.5 w-36"} />
              <Skeleton className="h-3 w-32" />
            </div>
            <Skeleton className="h-6 w-11 shrink-0 rounded-full" />
            <Skeleton className="size-8 shrink-0 rounded-lg" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** A Knowledge sub-page on its way: the search and a card of rows (under the tabs of the layout). */
export function KnowledgePageSkeleton() {
  return (
    <div aria-hidden className="space-y-6">
      <Skeleton className="h-10 w-full rounded-lg" />
      <div className="overflow-hidden rounded-2xl border border-line bg-surface">
        <div className="flex flex-wrap items-center gap-3 border-b border-line px-4 py-3 sm:px-6">
          <Skeleton className="h-9 w-40 rounded-lg" />
          <Skeleton className="h-9 w-32 rounded-lg" />
          <Skeleton className="ms-auto h-9 w-28 rounded-lg" />
        </div>
        <KnowledgeRowsSkeleton />
      </div>
    </div>
  );
}
