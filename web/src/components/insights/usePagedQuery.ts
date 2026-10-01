"use client";

import { useCallback, useEffect, useEffectEvent, useRef, useState, type DependencyList } from "react";

import { toApiError, type ApiError } from "@/api/errors";
import { unwrap, type ApiResult } from "@/api/result";

import { appendPage, PAGE_SIZE, reloadLimit, type PageShape } from "./paging";

export interface PageRequest {
  /** The previous page's `next_cursor`; null for the first page. */
  cursor: string | null;
  limit: number;
}

export interface PagedQuery<Item, Page> {
  /** The latest first-page answer (status counts and other totals live there). */
  page: Page | undefined;
  /** Every item loaded so far: the first page plus "show more" pages. */
  items: Item[] | undefined;
  error: ApiError | null;
  /** The last "show more" failed (the shown items stay). */
  moreError: ApiError | null;
  /** True until the first page for the current dependencies has arrived. */
  isLoading: boolean;
  hasMore: boolean;
  isLoadingMore: boolean;
  /** Load the next page and append it. */
  loadMore: () => void;
  /** Load the first pages again (as many items as are shown). */
  reload: () => void;
  /** Change loaded items locally (after a mutation). */
  updateItems: (update: (items: Item[]) => Item[]) => void;
  /** Change the first-page answer locally (counts after a mutation). */
  updatePage: (update: (page: Page) => Page) => void;
}

interface PagedState<Item, Page> {
  key: readonly unknown[];
  page: Page | undefined;
  items: Item[] | undefined;
  nextCursor: string | null;
  error: ApiError | null;
}

function sameKey(left: readonly unknown[], right: readonly unknown[]): boolean {
  return left.length === right.length && left.every((value, index) => Object.is(value, right[index]));
}

/**
 * A server-paged list with "show more". `deps` work like useEffect's: when
 * they change the list starts again from the first page; `reload()` keeps
 * the number of shown items (auto-refresh does not collapse the list).
 *
 *     const leads = usePagedQuery(
 *       ({ cursor, limit }) => api.GET("/v1/businesses/{business_id}/leads", {
 *         params: { path: { business_id }, query: { cursor: cursor ?? undefined, limit: String(limit) } },
 *       }),
 *       [business_id, status],
 *     );
 */
export function usePagedQuery<Item extends { id: string }, Page extends PageShape<Item>>(
  fetchPage: (request: PageRequest) => Promise<ApiResult<Page>>,
  deps: DependencyList,
  options: { enabled?: boolean; pageSize?: number } = {},
): PagedQuery<Item, Page> {
  const enabled = options.enabled ?? true;
  const pageSize = options.pageSize ?? PAGE_SIZE;
  const [generation, setGeneration] = useState(0);
  const [state, setState] = useState<PagedState<Item, Page> | null>(null);
  const [more, setMore] = useState<{ key: readonly unknown[]; isLoading: boolean; error: ApiError | null } | null>(
    null,
  );
  const fetchRef = useRef(fetchPage);
  // Items shown for the dependencies of the last first-page load.
  const shown = useRef<{ deps: readonly unknown[]; count: number }>({ deps: [], count: 0 });
  const key = [...deps, generation];

  useEffect(() => {
    fetchRef.current = fetchPage;
  });

  const loadFirst = useEffectEvent((request: PageRequest) => unwrap(fetchPage(request)));

  useEffect(() => {
    if (!enabled) {
      return;
    }
    let active = true;
    const requestKey = [...deps, generation];
    const sameFilters = sameKey(shown.current.deps, deps);
    loadFirst({ cursor: null, limit: sameFilters ? reloadLimit(shown.current.count, pageSize) : pageSize }).then(
      (page) => {
        if (active) {
          const items = page.items ?? [];
          shown.current = { deps, count: items.length };
          setState({ key: requestKey, page, items, nextCursor: page.next_cursor ?? null, error: null });
        }
      },
      (error: unknown) => {
        if (active) {
          setState((previous) => ({
            key: requestKey,
            page: previous?.page,
            items: previous?.items,
            nextCursor: previous?.nextCursor ?? null,
            error: toApiError(error),
          }));
        }
      },
    );
    return () => {
      active = false;
    };
    // The caller's dependency list drives reloading, as with useEffect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, generation, enabled, pageSize]);

  const isCurrent = state !== null && sameKey(state.key, key);
  const nextCursor = isCurrent ? state.nextCursor : null;
  const currentMore = more !== null && state !== null && sameKey(more.key, state.key) ? more : null;
  const isLoadingMore = currentMore?.isLoading ?? false;

  const loadMore = useCallback(() => {
    if (!state || !nextCursor || isLoadingMore) {
      return;
    }
    const requestKey = state.key;
    setMore({ key: requestKey, isLoading: true, error: null });
    unwrap(fetchRef.current({ cursor: nextCursor, limit: pageSize })).then(
      (page) => {
        setState((previous) => {
          if (!previous || !sameKey(previous.key, requestKey)) {
            return previous;
          }
          const items = appendPage(previous.items ?? [], page.items ?? []);
          shown.current = { ...shown.current, count: items.length };
          return { ...previous, items, nextCursor: page.next_cursor ?? null };
        });
        setMore({ key: requestKey, isLoading: false, error: null });
      },
      (error: unknown) => setMore({ key: requestKey, isLoading: false, error: toApiError(error) }),
    );
  }, [state, nextCursor, isLoadingMore, pageSize]);

  const reload = useCallback(() => setGeneration((value) => value + 1), []);
  const updateItems = useCallback((update: (items: Item[]) => Item[]) => {
    setState((previous) => {
      if (!previous) {
        return previous;
      }
      const items = update(previous.items ?? []);
      shown.current = { ...shown.current, count: items.length };
      return { ...previous, items };
    });
  }, []);
  const updatePage = useCallback((update: (page: Page) => Page) => {
    setState((previous) => (previous?.page ? { ...previous, page: update(previous.page) } : previous));
  }, []);

  return {
    page: state?.page,
    items: state?.items,
    error: isCurrent ? state.error : null,
    moreError: currentMore?.error ?? null,
    isLoading: enabled && !isCurrent,
    hasMore: nextCursor !== null,
    isLoadingMore,
    loadMore,
    reload,
    updateItems,
    updatePage,
  };
}
