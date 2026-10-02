"use client";

/**
 * A server-paged list ({items, next_cursor}) with "show more", cached like
 * any query (going back shows the list at once):
 *
 *     const leads = useCursorPage(queryKeys.leads.list(businessId, tab, includeTest), ({ cursor, limit }) =>
 *       api.GET("/v1/businesses/{business_id}/leads", {
 *         params: { path: { business_id: businessId }, query: { status, limit: String(limit), cursor: cursor ?? undefined } },
 *       }),
 *     );
 *     leads.items; leads.page?.status_counts; leads.hasMore; leads.loadMore();
 *
 * A reload asks for as many items as are shown, so a list extended with
 * "show more" keeps its length. While another key (other filters) loads,
 * the previous list stays as a dimmed placeholder (`isPlaceholder`); if the
 * new key fails, its error shows instead: the old items would read as the
 * filtered result.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { ApiError } from "./errors";
import { toApiError } from "./errors";
import { fromFirstPage, PAGE_SIZE, reloadLimit, withNextPage, type PageRequest, type PageShape, type PagedData } from "./paging";
import { queryCache } from "./queryCache";
import { hashKey, type QueryKey } from "./queryKey";
import { unwrap, type ApiResult } from "./result";
import { useCachedQuery, type QueryOptions } from "./useQuery";

export type { PageRequest } from "./paging";

export interface CursorPage<Item, Page> {
  /** The latest first-page answer (status counts and other totals live there). */
  page: Page | undefined;
  /** Every item loaded so far; undefined until the first page arrived. */
  items: Item[] | undefined;
  /** The first page failed (shown items, if any, are from before). */
  error: ApiError | null;
  /** Nothing loaded for this key yet. */
  isLoading: boolean;
  /** The first page is loading (a reload, or other filters). */
  isFetching: boolean;
  /** The shown items belong to the previous filters while the new ones load. */
  isPlaceholder: boolean;
  hasMore: boolean;
  isLoadingMore: boolean;
  /** The last "show more" failed (the shown items stay). */
  moreError: ApiError | null;
  loadMore: () => void;
  /** Load the first pages again (as many items as are shown). */
  reload: () => void;
  /** Change loaded items locally (after a mutation). */
  updateItems: (update: (items: Item[]) => Item[]) => void;
  /** Change the first-page answer locally (counts after a mutation). */
  updatePage: (update: (page: Page) => Page) => void;
}

export interface CursorPageOptions<Item> extends Omit<QueryOptions, "requireFresh"> {
  /** Items asked for per page (default 50). */
  pageSize?: number;
  /** The identity of an item, to skip repeats between pages (default: its `id`). */
  itemKey?: (item: Item) => string;
}

interface MoreState {
  hash: string;
  isLoading: boolean;
  error: ApiError | null;
}

export function useCursorPage<Item, Page extends PageShape<Item>>(
  key: QueryKey,
  fetchPage: (request: PageRequest) => Promise<ApiResult<Page>>,
  options: CursorPageOptions<Item> = {},
): CursorPage<Item, Page> {
  const { pageSize = PAGE_SIZE, itemKey, keepPreviousData = true, ...queryOptions } = options;
  const hash = hashKey(key);
  const stableKey = useMemo(() => JSON.parse(hash) as QueryKey, [hash]);
  const fetchRef = useRef(fetchPage);
  const itemKeyRef = useRef(itemKey);
  useEffect(() => {
    fetchRef.current = fetchPage;
    itemKeyRef.current = itemKey;
  });

  const query = useCachedQuery<PagedData<Item, Page>>(
    stableKey,
    async () => {
      const shown = queryCache.get<PagedData<Item, Page>>(stableKey).data?.items.length ?? 0;
      const limit = shown > 0 ? reloadLimit(shown, pageSize) : pageSize;
      return fromFirstPage<Item, Page>(await unwrap(fetchRef.current({ cursor: null, limit })));
    },
    { ...queryOptions, keepPreviousData },
  );

  const [more, setMore] = useState<MoreState>({ hash, isLoading: false, error: null });
  const currentMore = more.hash === hash ? more : { hash, isLoading: false, error: null };
  const data = query.data;
  const nextCursor = query.isPlaceholder ? null : (data?.nextCursor ?? null);

  const loadMore = useCallback(() => {
    if (!nextCursor || currentMore.isLoading) {
      return;
    }
    const cursor = nextCursor;
    setMore({ hash, isLoading: true, error: null });
    unwrap(fetchRef.current({ cursor, limit: pageSize })).then(
      (page) => {
        queryCache.setData<PagedData<Item, Page>>(
          stableKey,
          (current) => withNextPage(current, cursor, page, itemKeyRef.current),
          // Appending is not an edit: a reload already running may finish.
          { supersedeFetch: false },
        );
        setMore((state) => (state.hash === hash ? { hash, isLoading: false, error: null } : state));
      },
      (error: unknown) =>
        setMore((state) => (state.hash === hash ? { hash, isLoading: false, error: toApiError(error) } : state)),
    );
  }, [nextCursor, currentMore.isLoading, hash, pageSize, stableKey]);

  const { setData } = query;
  const updateItems = useCallback(
    (update: (items: Item[]) => Item[]) =>
      setData((current) => (current ? { ...current, items: update(current.items) } : current)),
    [setData],
  );
  const updatePage = useCallback(
    (update: (page: Page) => Page) => setData((current) => (current ? { ...current, page: update(current.page) } : current)),
    [setData],
  );

  return {
    page: data?.page,
    items: data?.items,
    error: query.error,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isPlaceholder: query.isPlaceholder,
    hasMore: nextCursor !== null,
    isLoadingMore: currentMore.isLoading,
    moreError: currentMore.error,
    loadMore,
    reload: query.reload,
    updateItems,
    updatePage,
  };
}
