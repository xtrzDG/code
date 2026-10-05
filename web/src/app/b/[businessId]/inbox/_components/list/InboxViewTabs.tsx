"use client";

/**
 * The views of the inbox with their live counts, as one segmented row; a
 * pill glides behind the chosen one. The three views staff work from
 * (Needs a person, Requests, Mine) are native radio buttons: arrow keys
 * move the choice and screen readers say "Mine, 2 conversations, 1 of 3".
 * Unassigned and All sit under "More ▾" (a menu of radio items); a view
 * chosen there takes the More button's place in full, so the chosen view
 * is never cut. Where even three do not fit (a phone, the list column
 * beside a conversation in Georgian) they scroll sideways with the hidden
 * side faded, and the chosen one is scrolled into sight.
 */

import { LayoutGroup } from "motion/react";
import * as m from "motion/react-m";
import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

import { IconCheck, IconChevronDown } from "@/components/icons";
import { ScrollRow } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { springTransition } from "@/lib/motion";
import type { InboxView } from "@/lib/navigation";

import { viewCount } from "../../_lib/inboxModel";
import type { InboxViewCounts } from "../../_lib/types";
import { MORE_INBOX_VIEWS, PRIMARY_INBOX_VIEWS, isMoreInboxView, menuTarget } from "../../_lib/viewTabs";

/** Views whose waiting conversations call for attention, and the tone of their number. */
const URGENT_VIEWS: ReadonlySet<InboxView> = new Set(["needs_person"]);

const TAB_CLASSES =
  "relative flex min-h-9 shrink-0 cursor-pointer items-center gap-1.5 rounded-lg px-3 text-sm font-medium whitespace-nowrap transition-colors select-none";

function ChosenPill() {
  return (
    <m.span
      layoutId="inbox-view-pill"
      transition={springTransition("snappy")}
      aria-hidden
      className="absolute inset-0 rounded-lg bg-surface shadow-sm ring-1 ring-line-strong/40"
    />
  );
}

function CountChip({ view, count, checked }: { view: InboxView; count: number; checked: boolean }) {
  return (
    <span
      aria-hidden
      className={cn(
        "relative min-w-5 rounded-full px-1.5 text-center text-xs tabular-nums",
        count > 0 && URGENT_VIEWS.has(view)
          ? "bg-warning-soft font-semibold text-warning"
          : checked
            ? "bg-accent-soft text-accent-ink"
            : "bg-surface/60 text-ink-subtle",
      )}
    >
      {count}
    </span>
  );
}

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
    <fieldset className="min-w-0">
      <legend className="sr-only">{t("inbox.viewsLabel")}</legend>
      <LayoutGroup id={name}>
        <div className="flex w-fit max-w-full items-center gap-0.5 rounded-xl bg-surface-muted p-1" data-inbox-views="">
          <ScrollRow className="min-w-0">
            <div className="flex w-max gap-0.5">
              {PRIMARY_INBOX_VIEWS.map((view) => {
                const checked = view === value;
                const count = viewCount(view, counts);
                return (
                  <label
                    key={view}
                    ref={checked ? chosenRef : undefined}
                    data-inbox-view={view}
                    className={cn(
                      TAB_CLASSES,
                      "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-1 has-[:focus-visible]:outline-focus",
                      checked ? "text-ink" : "text-ink-muted hover:text-ink",
                    )}
                  >
                    {checked ? <ChosenPill /> : null}
                    <input type="radio" name={name} value={view} checked={checked} onChange={() => onChange(view)} className="sr-only" />
                    <span className="relative">{t(`inbox.views.${view}`)}</span>
                    {count !== undefined ? (
                      <>
                        <CountChip view={view} count={count} checked={checked} />
                        <span className="sr-only">, {tp("inbox.viewCount", count)}</span>
                      </>
                    ) : null}
                  </label>
                );
              })}
            </div>
          </ScrollRow>
          <MoreViews value={value} counts={counts} onChange={onChange} />
        </div>
      </LayoutGroup>
    </fieldset>
  );
}

/** "More ▾": Unassigned and All as a menu of radio items; the chosen one shows on the button. */
function MoreViews({
  value,
  counts,
  onChange,
}: {
  value: InboxView;
  counts: InboxViewCounts | null;
  onChange: (view: InboxView) => void;
}) {
  const { t, tp } = useI18n();
  const id = useId();
  const [isOpen, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const chosen = isMoreInboxView(value) ? value : null;
  const chosenCount = chosen ? viewCount(chosen, counts) : undefined;

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const onPointer = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointer);
    const items = menu.current?.querySelectorAll<HTMLElement>('[role="menuitemradio"]');
    (menu.current?.querySelector<HTMLElement>('[aria-checked="true"]') ?? items?.[0])?.focus();
    return () => document.removeEventListener("pointerdown", onPointer);
  }, [isOpen]);

  const close = () => {
    setOpen(false);
    trigger.current?.focus();
  };
  const choose = (view: InboxView) => {
    close();
    if (view !== value) {
      onChange(view);
    }
  };
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const items = [...(menu.current?.querySelectorAll<HTMLElement>('[role="menuitemradio"]') ?? [])];
    const target = menuTarget(event.key, items.indexOf(document.activeElement as HTMLElement), items.length);
    if (event.key === "Escape" || event.key === "Tab") {
      event.preventDefault();
      close();
    } else if (target !== null) {
      event.preventDefault();
      items[target]?.focus();
    }
  };

  const chosenName = chosen ? t(`inbox.views.${chosen}`) : null;
  return (
    <div ref={root} className="relative shrink-0">
      <button
        ref={trigger}
        type="button"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-controls={isOpen ? `${id}-menu` : undefined}
        aria-label={
          chosenName
            ? [t("inbox.moreViewsChosen", { view: chosenName }), chosenCount !== undefined ? tp("inbox.viewCount", chosenCount) : null]
                .filter(Boolean)
                .join(", ")
            : undefined
        }
        data-more-views=""
        data-chosen={chosen ?? undefined}
        onClick={() => setOpen((open) => !open)}
        className={cn(TAB_CLASSES, "pe-2 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus", chosen ? "text-ink" : "text-ink-muted hover:text-ink")}
      >
        {chosen ? <ChosenPill /> : null}
        <span className="relative">{chosenName ?? t("inbox.moreViews")}</span>
        {chosen && chosenCount !== undefined ? <CountChip view={chosen} count={chosenCount} checked /> : null}
        <IconChevronDown className={cn("relative size-4 transition-transform", isOpen && "rotate-180")} aria-hidden />
      </button>
      {isOpen ? (
        <div
          ref={menu}
          id={`${id}-menu`}
          role="menu"
          aria-label={t("inbox.moreViews")}
          onKeyDown={onKeyDown}
          className="animate-settle absolute end-0 top-full z-30 mt-2 min-w-56 overflow-hidden rounded-xl border border-line bg-surface py-1 shadow-2xl"
        >
          {MORE_INBOX_VIEWS.map((view) => {
            const count = viewCount(view, counts);
            const checked = view === value;
            return (
              <button
                key={view}
                type="button"
                role="menuitemradio"
                aria-checked={checked}
                data-inbox-view={view}
                onClick={() => choose(view)}
                className="flex min-h-11 w-full items-center gap-2 px-3 text-start text-sm text-ink hover:bg-surface-muted focus-visible:bg-surface-muted focus-visible:outline-none"
              >
                <IconCheck className={cn("size-4 shrink-0 text-accent", !checked && "invisible")} aria-hidden />
                <span className="flex-1">{t(`inbox.views.${view}`)}</span>
                {count !== undefined ? (
                  <span className="text-xs text-ink-subtle tabular-nums">
                    <span aria-hidden>{count}</span>
                    <span className="sr-only">{tp("inbox.viewCount", count)}</span>
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
