/**
 * The cabinet's client-side data cache: one entry per query key, shared by
 * every screen, so going back to a page shows its data at once while a
 * fresh copy loads behind it (stale-while-revalidate).
 *
 * Screens read it through `useQuery` / `useCursorPage` (useSyncExternalStore);
 * mutations change it locally (`update`, `setData`) and mark what the server
 * changed as out of date (`invalidate`). `invalidate(prefix)` is public: the
 * live event stream calls it when the server reports a change.
 *
 * Nothing is fetched or stored while rendering on the server: entries are
 * created only by effects and event handlers in the browser, and a full page
 * load (sign-in, sign-out) starts from an empty cache.
 */

import { toApiError } from "./errors";
import { hashKey, startsWithKey, type QueryKey } from "./queryKey";
import { EMPTY_SNAPSHOT, type QuerySnapshot, type Rollback } from "./querySnapshot";

export type { QueryKey, QueryKeyPart } from "./queryKey";
export { EMPTY_SNAPSHOT, type QuerySnapshot, type Rollback } from "./querySnapshot";

/** Unobserved entries are dropped after this long. */
const DEFAULT_GC_MS = 5 * 60_000;
/** At most this many entries; the oldest unobserved ones go first. */
const MAX_ENTRIES = 400;

interface Entry {
  readonly key: QueryKey;
  readonly hash: string;
  snapshot: QuerySnapshot<unknown>;
  readonly listeners: Set<() => void>;
  /** The last fetcher given for the key, used to reload it on invalidation. */
  fetcher: (() => Promise<unknown>) | null;
  inflight: Promise<void> | null;
  /** Increases with every load; only the latest load's answer is kept. */
  fetchId: number;
  /**
   * Increases with every local write and invalidation: an answer to a load
   * that started before may predate that change, so it is dropped.
   */
  epoch: number;
  gcTimer: ReturnType<typeof setTimeout> | null;
}

export class QueryCache {
  private readonly entries = new Map<string, Entry>();
  private readonly invalidationListeners = new Set<(prefix: QueryKey) => void>();
  private readonly now: () => number;
  private readonly gcMs: number;

  constructor(options: { now?: () => number; gcMs?: number } = {}) {
    this.now = options.now ?? Date.now;
    this.gcMs = options.gcMs ?? DEFAULT_GC_MS;
  }

  /** The current state of a key (a stable object until it changes). */
  get<T>(key: QueryKey): QuerySnapshot<T> {
    return (this.entries.get(hashKey(key))?.snapshot ?? EMPTY_SNAPSHOT) as QuerySnapshot<T>;
  }

  /** Calls `listener` whenever the key's snapshot changes; returns the unsubscribe. */
  subscribe(key: QueryKey, listener: () => void): () => void {
    const entry = this.ensure(key);
    entry.listeners.add(listener);
    this.cancelGc(entry);
    return () => {
      entry.listeners.delete(listener);
      this.scheduleGc(entry);
    };
  }

  /**
   * Loads the key unless its data is younger than `staleMs` (and not
   * invalidated). A load already running for the key is shared, not repeated;
   * `force` starts a new one anyway (Refresh). Never rejects: a failure lands
   * in the snapshot's `error`.
   */
  fetch<T>(key: QueryKey, fetcher: () => Promise<T>, options: { staleMs?: number; force?: boolean } = {}): Promise<void> {
    const entry = this.ensure(key);
    entry.fetcher = fetcher;
    this.scheduleGc(entry);
    if (!options.force && entry.inflight) {
      return entry.inflight;
    }
    if (!options.force && this.isFresh(entry, options.staleMs ?? 0)) {
      return Promise.resolve();
    }
    return this.start(entry);
  }

  /** Writes the key's data locally (a mutation's answer, an appended page, an optimistic change). */
  setData<T>(
    key: QueryKey,
    update: T | undefined | ((current: T | undefined) => T | undefined),
    options: { supersedeFetch?: boolean } = {},
  ): void {
    const entry = this.ensure(key);
    const current = entry.snapshot.data as T | undefined;
    const next =
      typeof update === "function" ? (update as (current: T | undefined) => T | undefined)(current) : update;
    if (Object.is(next, current)) {
      return;
    }
    if (options.supersedeFetch ?? true) {
      entry.epoch += 1;
    }
    this.write(entry, { data: next, error: null });
    this.scheduleGc(entry);
  }

  /**
   * Changes the data of every loaded key under `prefix` (an optimistic
   * update) and returns how to undo it. The undo leaves alone an entry whose
   * data changed again since (newer data from the server wins).
   */
  update<T>(prefix: QueryKey, change: (data: T, key: QueryKey) => T): Rollback {
    const touched: { entry: Entry; before: unknown; after: unknown }[] = [];
    for (const entry of this.entries.values()) {
      if (entry.snapshot.data === undefined || !startsWithKey(entry.key, prefix)) {
        continue;
      }
      const before = entry.snapshot.data;
      const after = change(before as T, entry.key);
      if (Object.is(after, before)) {
        continue;
      }
      entry.epoch += 1;
      this.write(entry, { data: after, error: null });
      touched.push({ entry, before, after });
    }
    return () => {
      for (const { entry, before, after } of touched) {
        if (Object.is(entry.snapshot.data, after)) {
          entry.epoch += 1;
          this.write(entry, { data: before });
        }
      }
    };
  }

  /**
   * Marks every key under `prefix` as out of date. Keys on screen load again
   * right away (unless `refetchActive: false`); the others when next shown.
   */
  invalidate(prefix: QueryKey, options: { refetchActive?: boolean } = {}): void {
    const refetchActive = options.refetchActive ?? true;
    for (const entry of [...this.entries.values()]) {
      if (!startsWithKey(entry.key, prefix)) {
        continue;
      }
      entry.epoch += 1;
      if (refetchActive && entry.listeners.size > 0 && entry.fetcher) {
        void this.start(entry);
      } else {
        this.write(entry, { isInvalidated: true });
      }
    }
    [...this.invalidationListeners].forEach((listener) => listener(prefix));
  }

  /** Calls `listener` with each prefix marked out of date (views derived from other sections); returns the unsubscribe. */
  onInvalidate(listener: (prefix: QueryKey) => void): () => void {
    this.invalidationListeners.add(listener);
    return () => void this.invalidationListeners.delete(listener);
  }

  /** Forgets every entry (tests; a session that ends without a page load). */
  clear(): void {
    for (const entry of this.entries.values()) {
      this.cancelGc(entry);
    }
    this.entries.clear();
  }

  /** How many keys are cached (tests). */
  get size(): number {
    return this.entries.size;
  }

  private isFresh(entry: Entry, staleMs: number): boolean {
    const { data, isInvalidated, updatedAt } = entry.snapshot;
    return data !== undefined && !isInvalidated && this.now() - updatedAt < staleMs;
  }

  private start(entry: Entry): Promise<void> {
    const fetcher = entry.fetcher;
    if (!fetcher) {
      return Promise.resolve();
    }
    entry.fetchId += 1;
    const fetchId = entry.fetchId;
    const epoch = entry.epoch;
    this.write(entry, { isFetching: true });
    const promise = Promise.resolve()
      .then(fetcher)
      .then(
        (data) => {
          if (entry.fetchId !== fetchId) {
            return;
          }
          entry.inflight = null;
          if (entry.epoch !== epoch) {
            // Changed locally or on the server while this load ran: keep what
            // is shown and load again when next asked.
            this.write(entry, { isFetching: false, isInvalidated: true });
            return;
          }
          this.write(entry, { data, error: null, updatedAt: this.now(), isFetching: false, isInvalidated: false });
        },
        (error: unknown) => {
          if (entry.fetchId !== fetchId) {
            return;
          }
          entry.inflight = null;
          this.write(entry, { error: toApiError(error), isFetching: false });
        },
      );
    entry.inflight = promise;
    return promise;
  }

  private write(entry: Entry, patch: Partial<QuerySnapshot<unknown>>): void {
    entry.snapshot = { ...entry.snapshot, ...patch };
    for (const listener of [...entry.listeners]) {
      listener();
    }
  }

  private ensure(key: QueryKey): Entry {
    const hash = hashKey(key);
    const existing = this.entries.get(hash);
    if (existing) {
      return existing;
    }
    const entry: Entry = {
      key: [...key],
      hash,
      snapshot: EMPTY_SNAPSHOT,
      listeners: new Set(),
      fetcher: null,
      inflight: null,
      fetchId: 0,
      epoch: 0,
      gcTimer: null,
    };
    this.entries.set(hash, entry);
    this.evictOverflow();
    return entry;
  }

  private evictOverflow(): void {
    for (const entry of this.entries.values()) {
      if (this.entries.size <= MAX_ENTRIES) {
        return;
      }
      if (entry.listeners.size === 0 && !entry.inflight) {
        this.cancelGc(entry);
        this.entries.delete(entry.hash);
      }
    }
  }

  private scheduleGc(entry: Entry): void {
    if (entry.listeners.size > 0 || entry.gcTimer !== null) {
      return;
    }
    entry.gcTimer = setTimeout(() => {
      entry.gcTimer = null;
      if (entry.listeners.size > 0) {
        return;
      }
      if (entry.inflight) {
        this.scheduleGc(entry);
        return;
      }
      if (this.entries.get(entry.hash) === entry) {
        this.entries.delete(entry.hash);
      }
    }, this.gcMs);
  }

  private cancelGc(entry: Entry): void {
    if (entry.gcTimer !== null) {
      clearTimeout(entry.gcTimer);
      entry.gcTimer = null;
    }
  }
}

/** The cabinet's one cache. */
export const queryCache = new QueryCache();

/**
 * Marks every query under `prefix` as out of date and reloads the ones on screen
 * (`invalidate(queryKeys.leads(businessId))`): after mutations and live events.
 */
export function invalidate(prefix: QueryKey, options?: { refetchActive?: boolean }): void {
  queryCache.invalidate(prefix, options);
}
