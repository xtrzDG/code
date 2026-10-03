"use client";

/**
 * The views of the inbox side by side (Needs a person, Requests, Mine,
 * Unassigned, All) with their live counts, as one segmented row; a pill
 * glides behind the chosen one. Native radio buttons: arrow keys move the
 * choice and screen readers say "Mine, 2 conversations, 3 of 5". The row
 * never wraps: where it does not fit (a phone, the list column beside a
 * conversation) it scrolls sideways with its hidden side faded, and keeps
 * the chosen view in sight.
 */

import { LayoutGroup } from "motion/react";
import * as m from "motion/react-m";
import { useEffect, useId, useRef } from "react";

import { ScrollRow } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { springTransition } from "@/lib/motion";
import { INBOX_VIEWS, type InboxView } from "@/lib/navigation";

import { viewCount } from "../../_lib/inboxModel";
import type { InboxViewCounts } from "../../_lib/types";

/** Views whose waiting conversations call for attention, and the tone of their number. */
const URGENT_VIEWS: ReadonlySet<InboxView> = new Set(["needs_person"]);

export function InboxViewTabs({
  value,
  counts,
  onChange,
}: {
  value: InboxView;
  counts: InboxViewCounts | null;
  onChange: (view: InboxView) => void;
}) {
  const { t, tp } = useI18n();
  const name = useId();
  const chosenRef = useRef<HTMLLabelElement>(null);

  useEffect(() => {
    chosenRef.current?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [value]);

  return (
    <fieldset className="-mx-4 min-w-0 sm:mx-0">
      <legend className="sr-only">{t("inbox.viewsLabel")}</legend>
      <LayoutGroup id={name}>
        <ScrollRow className="px-4 sm:px-0">
          <div className="flex w-max gap-0.5 rounded-xl bg-surface-muted p-1" data-inbox-views="">
            {INBOX_VIEWS.map((view) => {
              const checked = view === value;
              const count = viewCount(view, counts);
              return (
                <label
                  key={view}
                  ref={checked ? chosenRef : undefined}
                  className={cn(
                    "relative flex min-h-9 shrink-0 cursor-pointer items-center gap-1.5 rounded-lg px-3 text-sm font-medium whitespace-nowrap transition-colors select-none",
                    "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-1 has-[:focus-visible]:outline-focus",
                    checked ? "text-ink" : "text-ink-muted hover:text-ink",
                  )}
                >
                  {checked ? (
                    <m.span
                      layoutId="inbox-view-pill"
                      transition={springTransition("snappy")}
                      aria-hidden
                      className="absolute inset-0 rounded-lg bg-surface shadow-sm ring-1 ring-line-strong/40"
                    />
                  ) : null}
                  <input
                    type="radio"
                    name={name}
                    value={view}
                    checked={checked}
                    onChange={() => onChange(view)}
                    className="sr-only"
                  />
                  <span className="relative">{t(`inbox.views.${view}`)}</span>
                  {count !== undefined ? (
                    <span
                      className={cn(
                        "relative min-w-5 rounded-full px-1.5 text-center text-xs tabular-nums",
                        count > 0 && URGENT_VIEWS.has(view)
                          ? "bg-warning-soft font-semibold text-warning"
                          : checked
                            ? "bg-accent-soft text-accent-ink"
                            : "bg-surface/60 text-ink-subtle",
                      )}
                    >
                      <span aria-hidden>{count}</span>
                      <span className="sr-only">, {tp("inbox.viewCount", count)}</span>
                    </span>
                  ) : null}
                </label>
              );
            })}
          </div>
        </ScrollRow>
      </LayoutGroup>
    </fieldset>
  );
}
