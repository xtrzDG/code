"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

import { useNiches } from "@/api/catalog";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { replaceUrlQuery } from "@/components/insights/urlQuery";

import { metricsQuery, metricsSearch, parseMetricsFilters, type MetricsFilters } from "./metrics";

/**
 * The founder's metrics for the filters in the address; a new filter
 * replaces the address (no navigation) and keeps the previous numbers on
 * screen, dimmed, until the new ones arrive.
 */
export function useAdminMetrics() {
  const searchParams = useSearchParams();
  const niches = useNiches();
  const filters = useMemo(() => parseMetricsFilters(new URLSearchParams(searchParams.toString())), [searchParams]);
  const query = metricsQuery(filters);
  const metrics = useQuery(
    queryKeys.admin.metrics(JSON.stringify(query)),
    () => api.GET("/v1/admin/metrics", { params: { query } }),
    { keepPreviousData: true },
  );
  const setFilters = useCallback((next: MetricsFilters) => replaceUrlQuery(metricsSearch(next)), []);
  const nicheName = (key: string) => niches.data?.niches.find((niche) => niche.key === key)?.name ?? key;
  return { filters, setFilters, metrics, nicheName };
}
