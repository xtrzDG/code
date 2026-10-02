/**
 * Placeholders shaped like the content that is loading, instead of a
 * spinner: the page keeps its layout and the data settles into it.
 *
 *     <LoadingRegion label={t("leads.loading")}>
 *       <SkeletonCard lines={3} />
 *     </LoadingRegion>
 *
 * Server-safe (no hooks): route `loading.tsx` files and screens use the same
 * pieces. Only `LoadingRegion` speaks to screen readers; the shapes are hidden.
 */

import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/cn";

/** One shimmering block; size it with classes (`h-4 w-32`, `size-10 rounded-full`). */
export function Skeleton({ className, style }: { className?: string; style?: CSSProperties }) {
  return (
    <span
      aria-hidden
      style={style}
      // skeleton-shimmer: a light sweeping across (a transform, src/styles/motion.css).
      className={cn("skeleton-shimmer block rounded-md bg-surface-muted", className)}
    />
  );
}

/** Lines of text; the last one shorter, like a paragraph. */
export function SkeletonText({ lines = 2, className }: { lines?: number; className?: string }) {
  return (
    <span aria-hidden className={cn("block space-y-2", className)}>
      {Array.from({ length: lines }, (_, index) => (
        <Skeleton key={index} className={cn("h-3", index === lines - 1 && lines > 1 ? "w-3/5" : "w-full")} />
      ))}
    </span>
  );
}

/**
 * The loading area: announced once to screen readers (`label`), busy until
 * the content replaces it.
 */
export function LoadingRegion({ label, className, children }: { label: string; className?: string; children: ReactNode }) {
  return (
    <div role="status" aria-busy="true" aria-live="polite" className={className}>
      <span className="sr-only">{label}</span>
      {children}
    </div>
  );
}

/** A card with a heading line and text lines (forms, settings blocks, details). */
export function SkeletonCard({ lines = 3, className, header = true }: { lines?: number; className?: string; header?: boolean }) {
  return (
    <div aria-hidden className={cn("rounded-2xl border border-line bg-surface", className)}>
      {header ? (
        <div className="space-y-2 border-b border-line px-5 py-4">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-3 w-64 max-w-full" />
        </div>
      ) : null}
      <div className="p-5">
        <SkeletonText lines={lines} />
      </div>
    </div>
  );
}

/** Rows of a list inside one card: an avatar or icon, a title and a line under it. */
export function SkeletonRows({ rows = 5, avatar = false, className }: { rows?: number; avatar?: boolean; className?: string }) {
  return (
    <div aria-hidden className={cn("divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface", className)}>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="flex items-start gap-3 px-4 py-3.5 sm:px-5">
          {avatar ? <Skeleton className="size-10 shrink-0 rounded-full" /> : null}
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex items-center justify-between gap-3">
              <Skeleton className={cn("h-3.5", index % 2 === 0 ? "w-36" : "w-28")} />
              <Skeleton className="h-3 w-12" />
            </div>
            <Skeleton className={cn("h-3", index % 3 === 0 ? "w-4/5" : "w-3/5")} />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Separate cards in a column (leads, handoffs): a title row, text and an action row. */
export function SkeletonCardList({ cards = 3, className }: { cards?: number; className?: string }) {
  return (
    <div aria-hidden className={cn("space-y-3", className)}>
      {Array.from({ length: cards }, (_, index) => (
        <div key={index} className="rounded-2xl border border-line bg-surface p-4 sm:p-5">
          <div className="flex flex-wrap items-center gap-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="ml-auto h-3 w-14" />
          </div>
          <SkeletonText lines={2} className="mt-3" />
          <div className="mt-4 flex items-center justify-between gap-3 border-t border-line pt-3">
            <Skeleton className="h-3.5 w-32" />
            <Skeleton className="h-8 w-28 rounded-lg" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** The title row of a page while the page itself is still on its way. */
export function SkeletonPageHeader({ actions = false }: { actions?: boolean }) {
  return (
    <div aria-hidden className="mb-6 flex flex-wrap items-end justify-between gap-4 sm:mb-8">
      <div className="space-y-2.5">
        <Skeleton className="h-6 w-48 sm:h-7" />
        <Skeleton className="h-3.5 w-72 max-w-[80vw]" />
      </div>
      {actions ? <Skeleton className="h-9 w-28 rounded-lg" /> : null}
    </div>
  );
}
