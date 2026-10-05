/**
 * The first queries of the sections the sidebar can load ahead of a click
 * (on hover or focus of the link), defined once so the prefetch and the
 * screen share the key and the request. Only lists that are not written to
 * the audit log are here: prefetching conversations, bookings, leads or
 * handoffs would record views of personal data nobody opened.
 */

import { api } from "./client";
import type { PageRequest } from "./paging";
import { queryKeys } from "./queryKeys";
import type { KnowledgeItemKind } from "./types";

import type { KnowledgeStatusFilter } from "@/lib/knowledge/kinds";

/** Knowledge items per request; "show more" loads the next page (newest first). */
const KNOWLEDGE_PAGE_SIZE = 100;

function isActiveQuery(status: KnowledgeStatusFilter): "true" | "false" | undefined {
  return status === "all" ? undefined : status === "active" ? "true" : "false";
}

export const sectionQueries = {
  dashboardStats: (businessId: string, from: string, to: string) => ({
    key: queryKeys.dashboard.stats(businessId, from, to),
    fetch: () =>
      api.GET("/v1/businesses/{business_id}/dashboard", {
        params: { path: { business_id: businessId }, query: { from, to } },
      }),
  }),

  knowledgeItems: (businessId: string, locale: string, kind: KnowledgeItemKind | "all", status: KnowledgeStatusFilter) => ({
    key: queryKeys.knowledge.items(businessId, locale, kind, status),
    pageSize: KNOWLEDGE_PAGE_SIZE,
    fetchPage: ({ cursor, limit }: PageRequest) =>
      api.GET("/v1/businesses/{business_id}/knowledge", {
        params: {
          path: { business_id: businessId },
          query: {
            language: locale,
            kind: kind === "all" ? undefined : kind,
            is_active: isActiveQuery(status),
            limit: String(limit),
            cursor: cursor ?? undefined,
          },
        },
      }),
  }),

  assistantVersions: (businessId: string) => ({
    key: queryKeys.assistant.versions(businessId),
    fetch: () =>
      api.GET("/v1/businesses/{business_id}/assistant-versions", { params: { path: { business_id: businessId } } }),
  }),

  channels: (businessId: string) => ({
    key: queryKeys.channels.list(businessId),
    fetch: () => api.GET("/v1/businesses/{business_id}/channels", { params: { path: { business_id: businessId } } }),
  }),

  billingOverview: (businessId: string, locale: string) => ({
    key: queryKeys.billing.overview(businessId, locale),
    fetch: () =>
      api.GET("/v1/businesses/{business_id}/billing", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
  }),
};
