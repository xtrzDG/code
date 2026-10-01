"use client";

import { useSearchParams, useSelectedLayoutSegment } from "next/navigation";
import { useMemo, useState, type ReactNode } from "react";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { RefreshButton } from "@/components/insights/common";
import { todayIn } from "@/components/insights/dates";
import { useAutoReload } from "@/components/insights/useAutoReload";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import { PageHeader } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { ConversationFiltersBar } from "./ConversationFiltersBar";
import { ConversationList } from "./ConversationList";
import {
  conversationFiltersQuery,
  filterConversations,
  parseConversationFilters,
  type ConversationFilters,
} from "./conversationModel";

/**
 * The conversations section: the feed with filters and, next to it on wide
 * screens (instead of it on phones), the open conversation.
 *
 * Filters live in the URL query so they survive opening a conversation,
 * going back and reloading; channel and test activity are filtered by the
 * API, status, period and search here.
 */
export function ConversationsShell({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const searchParams = useSearchParams();
  const selectedId = useSelectedLayoutSegment();
  const [today] = useState(() => todayIn(business.timezone));
  const businessId = business.id;

  const filters = useMemo(() => parseConversationFilters(new URLSearchParams(searchParams.toString())), [searchParams]);
  const query = conversationFiltersQuery(filters);

  const conversations = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/conversations", {
        params: {
          path: { business_id: businessId },
          query: {
            channel: filters.channel ?? undefined,
            include_sandbox: filters.includeTest ? "true" : undefined,
          },
        },
      }),
    [businessId, filters.channel, filters.includeTest],
  );
  useAutoReload(conversations.reload);

  const setFilters = (next: ConversationFilters) => {
    replaceUrlQuery(conversationFiltersQuery(next));
  };

  const all = conversations.data ?? [];
  const visible = filterConversations(all, filters, { today, timeZone: business.timezone });
  const isOpen = selectedId !== null;

  return (
    <>
      {isOpen ? <h1 className="sr-only lg:hidden">{t("nav.conversations")}</h1> : null}
      <div className={cn(isOpen && "hidden lg:block")}>
        <PageHeader
          title={t("nav.conversations")}
          description={t("pages.conversations.description")}
          actions={
            <RefreshButton
              onClick={conversations.reload}
              isRefreshing={conversations.isLoading && conversations.data !== undefined}
            />
          }
        />
      </div>

      <div className="lg:grid lg:grid-cols-[minmax(18rem,22rem)_minmax(0,1fr)] lg:items-start lg:gap-6">
        <section
          aria-label={t("conversations.listLabel")}
          className={cn(
            "space-y-3 lg:sticky lg:top-6 lg:flex lg:max-h-[calc(100dvh-3rem)] lg:flex-col",
            isOpen && "hidden lg:flex",
          )}
        >
          <ConversationFiltersBar filters={filters} onChange={setFilters} />
          <ConversationList
            key={query}
            query={conversations}
            items={visible}
            totalLoaded={all.length}
            selectedId={selectedId}
            linkQuery={query}
            onClearFilters={() => setFilters({ ...filters, status: null, period: "all", search: "", channel: null })}
          />
        </section>

        <div className={cn("min-w-0", !isOpen && "hidden lg:block")}>{children}</div>
      </div>
    </>
  );
}
