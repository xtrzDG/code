import { Skeleton } from "@/components/ui";

/** The six section cards while the profile loads. */
export function ProfileCardsSkeleton() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }, (_, index) => (
        <div key={index} className="flex h-36 gap-3 rounded-2xl border border-line bg-surface p-5">
          <Skeleton className="size-10 shrink-0 rounded-xl" />
          <div className="flex-1 space-y-2.5 pt-1">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-3.5 w-full max-w-56" />
            <Skeleton className="h-3.5 w-2/3" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** One section's editor while it loads: the way back, the section row and a few fields. */
export function SectionEditorSkeleton() {
  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-6 w-36 rounded-full" />
      </div>
      <div className="flex gap-2 overflow-hidden">
        {Array.from({ length: 6 }, (_, index) => (
          <Skeleton key={index} className="h-9 w-24 shrink-0 rounded-full" />
        ))}
      </div>
      <Skeleton className="h-7 w-56" />
      <Skeleton className="h-4 w-full max-w-lg" />
      <div className="space-y-4 rounded-2xl border border-line p-5">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-11 w-full" />
      </div>
    </div>
  );
}
