"use client";

/**
 * A server-paged list ({items, next_cursor}) with "show more":
 *
 *     const items = usePagedList(
 *       (cursor) => api.GET("/v1/businesses/{business_id}/knowledge", {
 *         params: { path: { business_id: id }, query: { kind, cursor: cursor ?? undefined } },
 *       }),
 *       [id, kind],
 *     );
 *     items.items; items.hasMore; items.loadMore();
 *
 * The dependency list (plain values) works like useApiQuery's: when it
 * changes, the list starts again from the first page, and a page still
 * loading for the previous list is dropped.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { toApiError, type ApiError } from "@/api/errors";
import { useApiQuery } from "@/api/hooks";
import { unwrap, type ApiResult } from "@/api/result";

export interface Page<T> {
  items?: T[];
  next_cursor?: string | null;
}

export interface PagedList<T> {
  /** Every item loaded so far, in the API's order. */
  items: T[];
  /** True until the first page of the current list has arrived. */
  isLoading: boolean;
  /** The first page failed (show it with a retry). */
  error: ApiError | null;
  hasMore: boolean;
  isLoadingMore: boolean;
  /** The last "show more" failed. */
  loadMoreError: ApiError | null;
  loadMore: () => void;
  /** Load the list again from the first page. */
  reload: () => void;
  /** Change loaded items locally (after an edit, a toggle or a delete). */
  update: (change: (items: T[]) => T[]) => void;
}

type ListKeyPart = string | number | boolean | null | undefined;

interface MoreState {
  key: string;
  isLoading: boolean;
  error: ApiError | null;
}

export function usePagedList<T extends { id: string }>(
  fetchPage: (cursor: string | null) => Promise<ApiResult<Page<T>>>,
  deps: readonly ListKeyPart[],
): PagedList<T> {
  const listKey = JSON.stringify(deps);
  const fetchRef = useRef(fetchPage);
  const latestKey = useRef(listKey);
  useEffect(() => {
    fetchRef.current = fetchPage;
    latestKey.current = listKey;
  });

  // The fetcher is read from a ref, so the list key alone decides when to load again.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const first = useApiQuery(() => fetchRef.current(null), [listKey]);
  const { data, setData, reload } = first;
  const [more, setMore] = useState<MoreState>({ key: listKey, isLoading: false, error: null });
  const current: MoreState = more.key === listKey ? more : { key: listKey, isLoading: false, error: null };
  const nextCursor = first.isLoading ? null : (data?.next_cursor ?? null);

  const loadMore = useCallback(() => {
    if (!nextCursor || current.isLoading) {
      return;
    }
    const requestKey = listKey;
    setMore({ key: requestKey, isLoading: true, error: null });
    unwrap(fetchRef.current(nextCursor)).then(
      (page) => {
        if (latestKey.current !== requestKey) {
          return;
        }
        setData((previous) => {
          const loaded = previous?.items ?? [];
          const known = new Set(loaded.map((item) => item.id));
          return {
            items: [...loaded, ...(page.items ?? []).filter((item) => !known.has(item.id))],
            next_cursor: page.next_cursor ?? null,
          };
        });
        setMore({ key: requestKey, isLoading: false, error: null });
      },
      (error: unknown) => {
        if (latestKey.current === requestKey) {
          setMore({ key: requestKey, isLoading: false, error: toApiError(error) });
        }
      },
    );
  }, [nextCursor, current.isLoading, listKey, setData]);

  const update = useCallback(
    (change: (items: T[]) => T[]) =>
      setData((previous) => ({ items: change(previous?.items ?? []), next_cursor: previous?.next_cursor ?? null })),
    [setData],
  );

  return {
    items: first.isLoading ? [] : (data?.items ?? []),
    isLoading: first.isLoading,
    error: first.error,
    hasMore: nextCursor !== null,
    isLoadingMore: current.isLoading,
    loadMoreError: current.error,
    loadMore,
    reload,
    update,
  };
}
