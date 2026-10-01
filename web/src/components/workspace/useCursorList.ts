"use client";

/**
 * A paged API list ({ items, next_cursor }) shown with "Show more":
 *
 *     const contacts = useCursorList(
 *       (cursor) => api.GET("/v1/businesses/{business_id}/contacts", {
 *         params: { path: { business_id }, query: { search, cursor: cursor ?? undefined } },
 *       }),
 *       (contact) => contact.id,
 *       [business_id, search],
 *     );
 *     contacts.items; contacts.hasMore; contacts.loadMore();
 *
 * The first page reloads when the dependencies change (the old items stay
 * on screen meanwhile, `isLoading` is true); `loadMore` appends the next
 * page and skips items already shown.
 */

import { useCallback, useEffect, useEffectEvent, useRef, useState, type DependencyList } from "react";

import { toApiError, type ApiError } from "@/api/errors";
import { unwrap, type ApiResult } from "@/api/result";

export interface CursorPage<Item> {
  items: Item[];
  next_cursor?: string | null;
}

export interface CursorList<Item, Page> {
  items: Item[];
  /** The latest first page as the API sent it (totals, filter choices…). */
  firstPage: Page | undefined;
  /** True until the first page for the current dependencies has arrived. */
  isLoading: boolean;
  /** The first page failed (for the current dependencies). */
  error: ApiError | null;
  hasMore: boolean;
  isLoadingMore: boolean;
  /** The last "show more" failed. */
  moreError: ApiError | null;
  loadMore: () => void;
  reload: () => void;
  /** Change the loaded items locally (after a mutation). */
  updateItems: (update: (items: Item[]) => Item[]) => void;
}

interface ListState<Item, Page> {
  key: readonly unknown[];
  items: Item[];
  firstPage: Page;
  nextCursor: string | null;
}

function sameKey(left: readonly unknown[], right: readonly unknown[]): boolean {
  return left.length === right.length && left.every((value, index) => Object.is(value, right[index]));
}

export function useCursorList<Item, Page extends CursorPage<Item>>(
  fetchPage: (cursor: string | null) => Promise<ApiResult<Page>>,
  itemKey: (item: Item) => string,
  deps: DependencyList,
): CursorList<Item, Page> {
  const [generation, setGeneration] = useState(0);
  const [state, setState] = useState<ListState<Item, Page> | null>(null);
  const [failure, setFailure] = useState<{ key: readonly unknown[]; error: ApiError } | null>(null);
  const [more, setMore] = useState<{ isLoading: boolean; error: ApiError | null }>({ isLoading: false, error: null });
  const fetchRef = useRef(fetchPage);
  const itemKeyRef = useRef(itemKey);
  const stateRef = useRef(state);
  const isLoadingMoreRef = useRef(false);
  const key = [...deps, generation];

  useEffect(() => {
    fetchRef.current = fetchPage;
    itemKeyRef.current = itemKey;
    stateRef.current = state;
  });

  const loadFirst = useEffectEvent(() => unwrap(fetchPage(null)));

  useEffect(() => {
    let active = true;
    const requestKey = [...deps, generation];
    loadFirst().then(
      (page) => {
        if (active) {
          setState({ key: requestKey, items: page.items, firstPage: page, nextCursor: page.next_cursor ?? null });
          setFailure(null);
          setMore({ isLoading: false, error: null });
        }
      },
      (error: unknown) => {
        if (active) {
          setFailure({ key: requestKey, error: toApiError(error) });
        }
      },
    );
    return () => {
      active = false;
    };
    // The caller's dependency list drives reloading, as with useEffect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, generation]);

  const loadMore = useCallback(() => {
    const current = stateRef.current;
    if (!current?.nextCursor || isLoadingMoreRef.current) {
      return;
    }
    isLoadingMoreRef.current = true;
    setMore({ isLoading: true, error: null });
    unwrap(fetchRef.current(current.nextCursor)).then(
      (page) => {
        isLoadingMoreRef.current = false;
        setMore({ isLoading: false, error: null });
        setState((previous) => {
          if (!previous || previous.key !== current.key) {
            return previous;
          }
          const shown = new Set(previous.items.map((item) => itemKeyRef.current(item)));
          const added = page.items.filter((item) => !shown.has(itemKeyRef.current(item)));
          return { ...previous, items: [...previous.items, ...added], nextCursor: page.next_cursor ?? null };
        });
      },
      (error: unknown) => {
        isLoadingMoreRef.current = false;
        setMore({ isLoading: false, error: toApiError(error) });
      },
    );
  }, []);

  const reload = useCallback(() => setGeneration((value) => value + 1), []);
  const updateItems = useCallback((update: (items: Item[]) => Item[]) => {
    setState((previous) => (previous ? { ...previous, items: update(previous.items) } : previous));
  }, []);

  const isCurrent = state !== null && sameKey(state.key, key);
  const isFailed = failure !== null && sameKey(failure.key, key);
  return {
    items: state?.items ?? [],
    firstPage: state?.firstPage,
    isLoading: !isCurrent && !isFailed,
    error: isFailed ? failure.error : null,
    hasMore: isCurrent && state.nextCursor !== null,
    isLoadingMore: more.isLoading,
    moreError: more.error,
    loadMore,
    reload,
    updateItems,
  };
}
