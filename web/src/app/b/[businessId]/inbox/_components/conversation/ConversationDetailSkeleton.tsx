import type { ReactNode } from "react";

import { LoadingRegion, Skeleton } from "@/components/ui";

const BUBBLES = [
  { side: "start", width: "w-3/5" },
  { side: "end", width: "w-1/2" },
  { side: "start", width: "w-2/5" },
  { side: "end", width: "w-3/5" },
] as const;

/**
 * The conversation card while it loads: the customer header (or `header`,
 * the real one drawn from the inbox list: ConversationHeaderPreview) and a
 * transcript of bubbles. Its own block (flow-root) keeps the header's
 * pull upwards on phones (shell.css) inside it, so the inbox around it stays put.
 */
export function ConversationDetailSkeleton({ label, header }: { label: string; header?: ReactNode }) {
  return (
    <LoadingRegion label={label} className="flow-root space-y-4">
      {header}
      <div aria-hidden className="rounded-2xl border border-line bg-surface p-5 [[data-conversation-preview]+&]:hidden">
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
