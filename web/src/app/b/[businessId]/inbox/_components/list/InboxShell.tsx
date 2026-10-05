"use client";

/**
 * The team inbox: its views with live counts, search and filters, the list
 * and, next to it on large screens (instead of it on phones), the open
 * conversation. The view and the filters live in the URL, so they survive
 * opening a conversation, going back and reloading; the list stays
 * mounted (it is the layout) while conversations open beside it.
 */

import { useSearchParams, useSelectedLayoutSegment } from "next/navigation";
import { useMemo, type ReactNode } from "react";

import { ExportCsvButton } from "@/components/exports/ExportCsvButton";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import { LiveStatus } from "@/components/shell/LiveStatus";
import { usePageHelp } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import {
  inboxApiQuery,
  inboxFiltersQuery,
  parseInboxFilters,
  sheetFilterCount,
  viewOnly,
  withView,
  type InboxFilters,
} from "../../_lib/inboxModel";
import { useInboxList } from "../../_lib/useInboxList";
import { useTeam } from "../../_lib/useTeam";
import { InboxList } from "./InboxList";
import { InboxToolbar } from "./InboxToolbar";
import { InboxViewTabs } from "./InboxViewTabs";

export function InboxShell({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const selectedId = useSelectedLayoutSegment();
  const filters = useMemo(() => parseInboxFilters(new URLSearchParams(searchParams.toString())), [searchParams]);
  const list = useInboxList(filters);
  const team = useTeam();
  const help = usePageHelp();
  const isOpen = selectedId !== null;
  const linkQuery = inboxFiltersQuery(filters);

  const setFilters = (next: InboxFilters) => replaceUrlQuery(inboxFiltersQuery(next));
  // The view and channel as CSV, every message included (owners only).
  const exportButton = (variant: "ghost" | "secondary", className?: string) => (
    <ExportCsvButton
      table="conversations"
      query={inboxApiQuery(filters)}
      label={t("dataExports.csv.inboxLabel")}
      hint={t("dataExports.csv.inboxHint")}
      variant={variant}
      className={className}
      iconOnly
    />
  );

  return (
    <div className="lg:grid lg:h-[calc(100dvh-4rem)] lg:grid-cols-[minmax(19rem,23rem)_minmax(0,1fr)] lg:gap-5 xl:grid-cols-[minmax(21rem,26.5rem)_minmax(0,1fr)]">
      <section
        aria-labelledby="inbox-title"
        className={cn("flex min-h-0 min-w-0 flex-col gap-3", isOpen && "hidden lg:flex")}
      >
        <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
          <div className="flex min-w-0 items-center gap-2">
            <h1 id="inbox-title" className="text-xl font-semibold tracking-tight text-ink sm:text-2xl">
              {t("inbox.title")}
            </h1>
            {/* The phone's top bar has its own "?". */}
            {help ? <div className="max-lg:hidden">{help}</div> : null}
          </div>
          <div className="flex items-center gap-2">
            <LiveStatus updatedAt={list.page.updatedAt} isFetching={list.page.isFetching && list.rows !== undefined} />
            {/* Phones: beside the title (the live status is a dot in the top bar); large screens: by the search. */}
            <div className="lg:hidden">{exportButton("ghost")}</div>
          </div>
        </header>
        <InboxViewTabs
          value={filters.view}
          counts={list.counts}
          onChange={(view) => setFilters(withView(filters, view))}
        />
        <InboxToolbar
          filters={filters}
          onChange={setFilters}
          trailing={<div className="hidden lg:block">{exportButton("secondary", "h-10 w-10")}</div>}
        />
        <InboxList
          list={list}
          filters={filters}
          team={team}
          selectedId={selectedId}
          linkQuery={linkQuery}
          hasFilters={sheetFilterCount(filters) > 0 || list.isFeed}
          onShowAll={() => setFilters(withView(filters, "all"))}
          onClearFilters={() => setFilters(viewOnly(filters))}
        />
      </section>

      {isOpen ? <h1 className="sr-only lg:hidden">{t("inbox.title")}</h1> : null}
      <div className={cn("min-h-0 min-w-0", !isOpen && "hidden lg:block")}>{children}</div>
    </div>
  );
}
