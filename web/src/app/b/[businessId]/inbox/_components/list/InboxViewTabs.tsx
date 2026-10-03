"use client";

/**
 * The views of the inbox side by side (Needs a person, Requests, Mine,
 * Unassigned, All) with their live counts; a soft pill glides behind the
 * chosen one. Native radio buttons: arrow keys move the choice and screen
 * readers say "Mine, 2 conversations, 3 of 5". On phones the row scrolls
 * sideways and keeps the chosen view in sight.
 */

import { LayoutGroup } from "motion/react";
import * as m from "motion/react-m";
import { useEffect, useId, useRef } from "react";

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
        <div className="flex snap-x gap-1 overflow-x-auto px-4 pb-1 [scrollbar-width:none] sm:px-0 lg:flex-wrap lg:overflow-visible">
          {INBOX_VIEWS.map((view) => {
            const checked = view === value;
            const count = viewCount(view, counts);
            return (
              <label
                key={view}
                ref={checked ? chosenRef : undefined}
                className={cn(
                  "relative flex min-h-10 shrink-0 cursor-pointer snap-start items-center gap-1.5 rounded-full px-3.5 text-sm font-medium whitespace-nowrap transition-colors select-none",
                  "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-1 has-[:focus-visible]:outline-focus",
                  checked ? "text-accent-ink" : "text-ink-muted hover:text-ink",
                )}
              >
                {checked ? (
                  <m.span
                    layoutId="inbox-view-pill"
                    transition={springTransition("snappy")}
                    aria-hidden
                    className="absolute inset-0 rounded-full bg-accent-soft ring-1 ring-accent/25"
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
                          ? "bg-surface/70 text-accent-ink"
                          : "bg-surface-muted text-ink-subtle",
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
      </LayoutGroup>
    </fieldset>
  );
}
