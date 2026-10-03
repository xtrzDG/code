import { Skeleton } from "@/components/ui";

/** Day groups of bookings while the list loads: a date header and timed rows, like the list. */
export function BookingDaysSkeleton({ days = 2 }: { days?: number }) {
  return (
    <div aria-hidden className="space-y-4">
      {Array.from({ length: days }, (_, day) => (
        <div key={day} className="overflow-hidden rounded-2xl border border-line bg-surface">
          <div className="flex items-center justify-between gap-3 border-b border-line bg-surface-muted/60 px-4 py-3 sm:px-5">
            <Skeleton className="h-3.5 w-40" />
            <Skeleton className="h-3 w-16" />
          </div>
          <div className="divide-y divide-line">
            {Array.from({ length: day === 0 ? 3 : 2 }, (_, row) => (
              <div key={row} className="flex items-start gap-3 px-4 py-3.5 sm:gap-4 sm:px-5">
                <Skeleton className="h-4 w-12 shrink-0 sm:w-16" />
                <div className="min-w-0 flex-1 space-y-2">
                  <Skeleton className={row % 2 === 0 ? "h-3.5 w-40" : "h-3.5 w-32"} />
                  <Skeleton className="h-3 w-56 max-w-full" />
                </div>
                <Skeleton className="h-5 w-20 shrink-0 rounded-full" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
