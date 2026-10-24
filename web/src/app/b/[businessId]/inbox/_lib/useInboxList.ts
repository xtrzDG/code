"use client";

/**
 * The list of the inbox for the filters in the URL: a view of GET …/inbox,
 * or, for a search or the history filters on "All", the conversation feed.
 * Both are paged and cached; the one not in use loads nothing. Every load
 * is audited, so there is no polling: the live stream reloads the list
 * when something changes, and it reloads when the person comes back.
 * The counts of the views come from GET …/inbox/counts (counts only, not
 * audited) and stay fresh with every event.
 */

import { useMemo } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage, type CursorPage } from "@/api/useCursorPage";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import type { ConversationPage, ConversationSummaryView } from "@/components/insights/types";
import { useAutoReload } from "@/components/insights/useAutoReload";
import { useToday } from "@/components/insights/useToday";

import {
  feedApiQuery,
  inboxApiQuery,
  inboxFiltersQuery,
  rowFromConversation,
  rowFromInboxItem,
  usesConversationFeed,
  type InboxFilters,
  type InboxRow,
} from "./inboxModel";
import type { InboxItemView, InboxPage, InboxViewCounts } from "./types";

export interface InboxList {
  rows: InboxRow[] | undefined;
  /** The paged query in use (loading, errors, "show more"). */
  page: CursorPage<unknown, unknown>;
  /** The list comes from the conversation feed (a search or history filters). */
  isFeed: boolean;
  counts: InboxViewCounts | null;
}

export function useInboxList(filters: InboxFilters): InboxList {
  const { business } = useBusiness();
  const businessId = business.id;
  const today = useToday(business.timezone);
  const isFeed = usesConversationFeed(filters);

  const inbox = useCursorPage<InboxItemView, InboxPage>(
    queryKeys.conversations.inbox(businessId, filters.view, filters.channel),
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/inbox", {
        params: {
          path: { business_id: businessId },
          query: { ...inboxApiQuery(filters), limit: String(limit), cursor: cursor ?? undefined },
        },
      }),
    { enabled: !isFeed },
  );
  const feed = useCursorPage<ConversationSummaryView, ConversationPage>(
    queryKeys.conversations.list(businessId, inboxFiltersQuery(filters), today),
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/conversations", {
        params: {
          path: { business_id: businessId },
          query: { ...feedApiQuery(filters, today), limit: String(limit), cursor: cursor ?? undefined },
        },
      }),
    { enabled: isFeed },
  );
  const views = useQuery(queryKeys.inbox.views(businessId), () =>
    api.GET("/v1/businesses/{business_id}/inbox/counts", { params: { path: { business_id: businessId } } }),
  );

  const active = isFeed ? feed : inbox;
  useAutoReload(active.reload, { intervalMs: null });

  const inboxItems = inbox.items;
  const feedItems = feed.items;
  const rows = useMemo(
    () => (isFeed ? feedItems?.map(rowFromConversation) : inboxItems?.map(rowFromInboxItem)),
    [isFeed, feedItems, inboxItems],
  );
  // The live counts; until they load, the ones that came with the page.
  const counts = views.data ?? inbox.page?.counts ?? null;

  return { rows, page: active as CursorPage<unknown, unknown>, isFeed, counts };
}
