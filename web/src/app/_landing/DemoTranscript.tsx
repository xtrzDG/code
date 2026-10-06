"use client";

import { useEffect, useRef, type ReactNode } from "react";

import { IconCalendar, IconClipboard, IconHandoff } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import type { DemoEntry, DemoFailure, DemoOutcome } from "@/lib/publicSite/demoChat";

const OUTCOME_ICONS: Record<DemoOutcome, typeof IconCalendar> = {
  booking: IconCalendar,
  request: IconClipboard,
  handoff: IconHandoff,
};

/**
 * The demo conversation: the assistant's greeting, the visitor's messages
 * and the answers (in their own language), what a sandbox turn would have
 * done, the typing dots and what went wrong. A polite live region, so a
 * screen reader hears each answer once.
 */
export function DemoTranscript({
  greeting,
  entries,
  isSending,
  failure,
}: {
  /** The assistant's first words, naming the business (user content). */
  greeting: ReactNode;
  entries: readonly DemoEntry[];
  isSending: boolean;
  failure: DemoFailure | null;
}) {
  const { t } = useI18n();
  const log = useRef<HTMLDivElement>(null);
  const bubble = "max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm whitespace-pre-line break-words";

  // Keep the newest message in view inside the box; the page itself never scrolls.
  useEffect(() => {
    const box = log.current;
    if (box && (entries.length > 0 || failure)) {
      box.scrollTop = box.scrollHeight;
    }
  }, [entries.length, isSending, failure]);

  return (
    <div ref={log} role="log" aria-live="polite" aria-relevant="additions" className="h-72 space-y-3 overflow-y-auto overscroll-contain px-4 py-4 sm:h-80">
      <p className={cn(bubble, "rounded-bl-md bg-accent-soft text-ink")}>{greeting}</p>
      {entries.map((entry) =>
        entry.role === "visitor" ? (
          <p key={entry.id} className={cn(bubble, "ml-auto rounded-br-md bg-surface-muted text-ink")} dir="auto" data-role="visitor">
            <span className="sr-only">{t("publicDemo.you")}: </span>
            <span data-user-content>{entry.text}</span>
          </p>
        ) : (
          <div key={entry.id} className="space-y-1.5">
            <p className={cn(bubble, "rounded-bl-md bg-accent-soft text-ink")} lang={entry.lang} dir="auto" data-role="assistant">
              <span className="sr-only">{t("publicDemo.assistant")}: </span>
              {entry.text}
            </p>
            {entry.outcomes.map((outcome) => {
              const Icon = OUTCOME_ICONS[outcome];
              return (
                <p
                  key={outcome}
                  className="flex w-fit items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-1 text-xs text-ink-muted"
                  data-testid={`demo-outcome-${outcome}`}
                >
                  <Icon className="size-3.5 shrink-0 text-accent" aria-hidden />
                  {t(`publicDemo.outcomes.${outcome}`)}
                </p>
              );
            })}
          </div>
        ),
      )}
      {isSending ? (
        <p className={cn(bubble, "flex w-fit items-center gap-1 rounded-bl-md bg-accent-soft text-ink-muted")}>
          <span className="sr-only">{t("publicDemo.typing")}</span>
          {[0, 1, 2].map((dot) => (
            <span
              key={dot}
              aria-hidden
              className="size-1.5 animate-pulse rounded-full bg-ink-subtle motion-reduce:animate-none"
              style={{ animationDelay: `${dot * 160}ms` }}
            />
          ))}
        </p>
      ) : null}
      {failure ? (
        <p role="alert" className="rounded-xl border border-warning/30 bg-warning-soft px-3 py-2 text-sm text-ink">
          {t(`publicDemo.failures.${failure}`)}
        </p>
      ) : null}
    </div>
  );
}
