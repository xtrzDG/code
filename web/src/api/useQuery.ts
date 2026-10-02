"use client";

/**
 * Reading API data through the shared cache (queryCache.ts):
 *
 *     const bookings = useQuery(queryKeys.resources.list(businessId), () =>
 *       api.GET("/v1/businesses/{business_id}/resources", { params: { path: { business_id: businessId } } }),
 *     );
 *     if (bookings.data === undefined) return bookings.error ? <ErrorState … /> : <ListSkeleton />;
 *
 * Data already in the cache shows at once (going back to a page); when it is
 * older than `staleMs` (or was invalidated) a fresh copy loads behind it.
 * The key decides what is loaded: a new key loads its own data, like the
 * dependency list of an effect.
 */

import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import type { ApiError } from "./errors";
import { EMPTY_SNAPSHOT, queryCache, type QuerySnapshot } from "./queryCache";
import { hashKey, type QueryKey } from "./queryKey";
import { unwrap, type ApiResult } from "./result";

/** Data younger than this is shown without loading it again. */
export const DEFAULT_STALE_MS = 30_000;

export interface QueryOptions {
  /** False: load nothing (yet); cached data, if any, is still returned. */
  enabled?: boolean;
  /** How long loaded data counts as fresh (default 30 s; 0: reload on every mount). */
  staleMs?: number;
  /** While a new key loads, keep returning the previous key's data (`isPlaceholder`). */
  keepPreviousData?: boolean;
  /**
   * Return only data loaded after this screen opened: forms that save with
   * the revision they started from must not start from a cached copy.
   */
  requireFresh?: boolean;
}

export interface Query<T> {
  /** The key's data (or, with `keepPreviousData`, the previous key's while it loads). */
  data: T | undefined;
  /** The last load failed (hidden while a retry runs and nothing is shown). */
  error: ApiError | null;
  /** Nothing loaded for this key yet: show a skeleton (or the placeholder). */
  isLoading: boolean;
  /** A load is running (Refresh spins while data is shown). */
  isFetching: boolean;
  /** `data` belongs to the previous key (dim it). */
  isPlaceholder: boolean;
  /** Load again now (the Refresh button, a retry). */
  reload: () => void;
  /** Change the cached data locally (after a mutation that returned it). */
  setData: (update: T | ((current: T | undefined) => T | undefined)) => void;
}

const serverSnapshot = () => EMPTY_SNAPSHOT;
const currentTime = () => Date.now();

/** `useQuery` on a loader that returns the data itself (or throws an ApiError). */
export function useCachedQuery<T>(key: QueryKey, load: () => Promise<T>, options: QueryOptions = {}): Query<T> {
  const { enabled = true, staleMs = DEFAULT_STALE_MS, keepPreviousData = false, requireFresh = false } = options;
  const hash = hashKey(key);
  const stableKey = useMemo(() => JSON.parse(hash) as QueryKey, [hash]);
  const loadRef = useRef(load);
  useEffect(() => {
    loadRef.current = load;
  });
  const run = useCallback(() => loadRef.current(), []);

  const subscribe = useCallback((listener: () => void) => queryCache.subscribe(stableKey, listener), [stableKey]);
  const getSnapshot = useCallback(() => queryCache.get<T>(stableKey), [stableKey]);
  const snapshot = useSyncExternalStore<QuerySnapshot<T>>(subscribe, getSnapshot, serverSnapshot);
  const [openedAt] = useState(currentTime);

  useEffect(() => {
    if (enabled) {
      void queryCache.fetch(stableKey, run, { staleMs: requireFresh ? 0 : staleMs });
    }
  }, [stableKey, enabled, staleMs, requireFresh, run]);

  const reload = useCallback(() => void queryCache.fetch(stableKey, run, { force: true }), [stableKey, run]);
  const setData = useCallback(
    (update: T | ((current: T | undefined) => T | undefined)) => queryCache.setData<T>(stableKey, update),
    [stableKey],
  );

  const isUsable = !requireFresh || snapshot.updatedAt >= openedAt;
  const data = isUsable ? snapshot.data : undefined;
  const isRetrying = data === undefined && snapshot.isFetching;
  const error = isRetrying ? null : snapshot.error;
  // A key that failed shows its error, not the previous key's data.
  const placeholder = usePlaceholder<T>(hash, data, keepPreviousData && error === null);

  return {
    data: data ?? placeholder,
    error,
    isLoading: enabled && data === undefined && error === null,
    isFetching: snapshot.isFetching,
    isPlaceholder: data === undefined && placeholder !== undefined,
    reload,
    setData,
  };
}

/**
 * The data of the last key that had some, while the current key has none
 * yet (filters changed: the old list stays, dimmed, until the new one comes).
 */
function usePlaceholder<T>(hash: string, data: T | undefined, enabled: boolean): T | undefined {
  const [shownHash, setShownHash] = useState<string | null>(null);
  if (enabled && data !== undefined && shownHash !== hash) {
    setShownHash(hash);
  }
  if (!enabled || data !== undefined || shownHash === null || shownHash === hash) {
    return undefined;
  }
  return queryCache.get<T>(JSON.parse(shownHash) as QueryKey).data;
}

/** Reads one API call through the cache; see the module comment. */
export function useQuery<T>(
  key: QueryKey,
  fetcher: () => Promise<ApiResult<T>>,
  options?: QueryOptions,
): Query<T> {
  return useCachedQuery(key, () => unwrap(fetcher()), options);
}

/**
 * Loads a key into the cache ahead of time (a section link under the
 * pointer), unless fresh data is already there. Never throws.
 */
export function prefetchQuery<T>(
  key: QueryKey,
  fetcher: () => Promise<ApiResult<T>>,
  options: { staleMs?: number } = {},
): Promise<void> {
  return queryCache.fetch(key, () => unwrap(fetcher()), { staleMs: options.staleMs ?? DEFAULT_STALE_MS });
}
