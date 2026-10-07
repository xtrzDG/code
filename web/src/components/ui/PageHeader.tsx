"use client";

import { createContext, useContext, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { Button } from "./Button";
import { usePageHelp } from "./PageHelp";
import { usePhoneChrome, usePhoneDescription, usePhoneFab, type PhoneFabAction } from "./PhoneChrome";

/** 1 on a page of its own; 2 inside a section frame, which owns the page's <h1>. */
type PageLevel = 1 | 2;

const PageLevelContext = createContext<PageLevel>(1);

/**
 * The pages of a section frame (Messages, Assistant, Settings): the frame
 * shows the section's <h1> and tabs, so each page's PageHeader inside
 * becomes an <h2> for screen readers, and shows only its description and
 * actions.
 */
export function SubPages({ children }: { children: ReactNode }) {
  return <PageLevelContext.Provider value={2}>{children}</PageLevelContext.Provider>;
}

/** Whether this part of the page is inside a section frame. */
export function usePageLevel(): PageLevel {
  return useContext(PageLevelContext);
}

/** The page's one main action: a button on large screens, the floating button on phones. */
export interface PagePrimaryAction extends PhoneFabAction {
  /** A longer explanation, as the button's tooltip. */
  hint?: string;
}

function PrimaryButton({ action, hideOnPhones }: { action: PagePrimaryAction; hideOnPhones: boolean }) {
  const Icon = action.icon;
  return (
    <Button
      leadingIcon={<Icon className="size-4" aria-hidden />}
      onClick={action.onClick}
      title={action.hint}
      aria-haspopup={action.opensDialog ? "dialog" : undefined}
      className={hideOnPhones ? "max-lg:hidden" : undefined}
    >
      {action.label}
    </Button>
  );
}

/**
 * The title row of a page: one <h1>, a description and page actions.
 *
 * In the cabinet's shell on a phone (below lg) the header collapses: the
 * title is the top bar's (the heading stays for screen readers), the
 * description sits behind the top bar's (i), `status` (the live status)
 * becomes its dot, and `primaryAction` the floating button above the tab
 * bar. Only `actions` stay on the page. The page's help (a "?" set by the
 * cabinet's frame, PageHelp) sits beside the <h1>; on phones it is in the
 * top bar.
 */
export function PageHeader({
  title,
  description,
  actions,
  status,
  primaryAction,
  eyebrow,
  tight = false,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  /** The page's live status (LiveStatus): beside the actions; a dot in the phone's top bar. */
  status?: ReactNode;
  primaryAction?: PagePrimaryAction;
  /** Small text above the title (a business name, a step number). */
  eyebrow?: ReactNode;
  /** Less room under the header on large screens (a section frame's tabs follow). */
  tight?: boolean;
  className?: string;
}) {
  const level = usePageLevel();
  const help = usePageHelp();
  const chrome = usePhoneChrome();
  const isCompact = chrome?.hasTopBar ?? false;
  const hasFab = chrome?.hasFabSlot ?? false;
  usePhoneDescription(level, isCompact && description ? { title, text: description } : null);
  usePhoneFab(level, hasFab ? primaryAction : undefined);

  const hideOnPhones = isCompact ? "max-lg:hidden" : undefined;
  const statusSlot = status ? <div className={hideOnPhones}>{status}</div> : null;
  const primary = primaryAction ? <PrimaryButton action={primaryAction} hideOnPhones={hasFab} /> : null;
  const hasActionRow = Boolean(actions || status || primaryAction);
  // What stays on a phone: the actions, an eyebrow, and a primary action without a floating slot.
  const showsOnPhones = Boolean(actions || eyebrow || (primaryAction && !hasFab) || (!isCompact && (description || status)));

  if (level === 2) {
    const hasText = Boolean(eyebrow || description);
    if (!hasText && !hasActionRow) {
      return <h2 className="sr-only">{title}</h2>;
    }
    return (
      <header
        className={cn(
          "flex flex-wrap items-center justify-between gap-x-4 gap-y-3",
          isCompact && !showsOnPhones ? "lg:mb-5" : "mb-5",
          className,
        )}
      >
        <h2 className="sr-only">{title}</h2>
        {hasText ? (
          <div className={cn("min-w-0 space-y-1", isCompact && !eyebrow && "max-lg:hidden")}>
            {eyebrow ? <p className="text-sm font-medium text-accent">{eyebrow}</p> : null}
            {description ? <p className={cn("max-w-3xl text-sm text-ink-muted", hideOnPhones)}>{description}</p> : null}
          </div>
        ) : null}
        {hasActionRow ? (
          <div className="ms-auto flex max-w-full min-w-0 flex-wrap items-center gap-2">
            {statusSlot}
            {actions}
            {primary}
          </div>
        ) : null}
      </header>
    );
  }

  return (
    <header
      className={cn(
        "flex flex-wrap items-end justify-between gap-4",
        !isCompact
          ? tight
            ? "mb-6"
            : "mb-6 sm:mb-8"
          : cn(showsOnPhones && "mb-4 max-lg:items-center", tight ? "lg:mb-6" : "lg:mb-8"),
        className,
      )}
    >
      <div className={cn("min-w-0 space-y-1.5", isCompact && !eyebrow && "max-lg:contents")}>
        {eyebrow ? <p className="text-sm font-medium text-accent">{eyebrow}</p> : null}
        <div className={cn("flex min-w-0 items-center gap-2", isCompact && "max-lg:contents")}>
          <h1 className={cn("text-xl font-semibold tracking-tight text-ink sm:text-2xl", isCompact && "max-lg:sr-only")}>{title}</h1>
          {help ? <div className={cn("shrink-0", isCompact && "max-lg:hidden")}>{help}</div> : null}
        </div>
        {description ? <p className={cn("max-w-3xl text-sm text-ink-muted", hideOnPhones)}>{description}</p> : null}
      </div>
      {hasActionRow ? (
        <div className={cn("flex max-w-full min-w-0 flex-wrap items-center gap-2", isCompact && !showsOnPhones && "max-lg:hidden")}>
          {statusSlot}
          {actions}
          {primary}
        </div>
      ) : null}
    </header>
  );
}
