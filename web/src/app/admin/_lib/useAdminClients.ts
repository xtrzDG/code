"use client";

import { useEffect, useState } from "react";

import { useNiches } from "@/api/catalog";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";

import {
  ADMIN_PAGE_SIZE,
  EMPTY_FILTERS,
  clientsQuery,
  type AdminClientPage,
  type AdminClientSummary,
  type ClientFilters,
  type ClientSort,
} from "./clients";

const SEARCH_DELAY_MS = 300;

/** The admin's client list: filters (the search waits for typing to pause), the sort and server paging. */
export function useAdminClients() {
  const niches = useNiches();
  const [filters, setFilters] = useState<ClientFilters>(EMPTY_FILTERS);
  const [search, setSearch] = useState<string | undefined>(undefined);
  const [sort, setSort] = useState<ClientSort>("health");

  useEffect(() => {
    const trimmed = filters.query.trim().slice(0, 100);
    const timer = window.setTimeout(() => setSearch(trimmed === "" ? undefined : trimmed), SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [filters.query]);

  const query = clientsQuery(filters, search, sort);
  const list = useCursorPage<AdminClientSummary, AdminClientPage>(
    queryKeys.admin.clients(JSON.stringify(query)),
    ({ cursor, limit }) =>
      api.GET("/v1/admin/clients", {
        params: { query: { ...query, limit: String(limit), ...(cursor ? { cursor } : {}) } },
      }),
    { pageSize: ADMIN_PAGE_SIZE, itemKey: (client) => client.business_id },
  );

  const nicheName = (key: string) => niches.data?.niches.find((niche) => niche.key === key)?.name ?? key;

  return { filters, setFilters, sort, setSort, list, nicheName };
}
