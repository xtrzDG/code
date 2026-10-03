/**
 * How live events reach the query cache: the keys a burst of events touches
 * are collected for a moment and each is invalidated once (a customer's
 * message and the answer a second later reload the list once). While the
 * tab is hidden only the counts reload (the tab title and the badges show
 * them); everything else is reloaded when the person comes back, so a
 * hidden tab neither loads lists nobody sees nor writes audit entries for
 * them.
 */

import { invalidate as invalidateCache, type QueryKey } from "./queryCache";
import { hashKey, startsWithKey } from "./queryKey";

/** Events closer together than this reload once. */
export const BATCH_MS = 200;

export interface LiveInvalidationOptions {
  /** Keys that reload even in a hidden tab (the counts). */
  alwaysFresh: readonly QueryKey[];
  invalidate?: (prefix: QueryKey, options: { refetchActive: boolean }) => void;
  isVisible?: () => boolean;
  batchMs?: number;
}

export class LiveInvalidation {
  private readonly alwaysFresh: readonly QueryKey[];
  private readonly invalidate: (prefix: QueryKey, options: { refetchActive: boolean }) => void;
  private readonly isVisible: () => boolean;
  private readonly batchMs: number;
  private readonly waiting = new Map<string, QueryKey>();
  private readonly whileHidden = new Map<string, QueryKey>();
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor(options: LiveInvalidationOptions) {
    this.alwaysFresh = options.alwaysFresh;
    this.invalidate = options.invalidate ?? ((prefix, invalidateOptions) => invalidateCache(prefix, invalidateOptions));
    this.isVisible = options.isVisible ?? (() => typeof document === "undefined" || document.visibilityState === "visible");
    this.batchMs = options.batchMs ?? BATCH_MS;
  }

  /** Marks these keys out of date (soon, together with the rest of the burst). */
  add(keys: readonly QueryKey[]): void {
    for (const key of keys) {
      this.waiting.set(hashKey(key), key);
    }
    if (this.timer === null) {
      this.timer = setTimeout(() => this.flush(), this.batchMs);
    }
  }

  /** The tab is shown again: reload what changed while it was hidden. */
  resume(): void {
    if (!this.isVisible() || this.whileHidden.size === 0) {
      return;
    }
    const keys = [...this.whileHidden.values()];
    this.whileHidden.clear();
    for (const key of keys) {
      this.invalidate(key, { refetchActive: true });
    }
  }

  dispose(): void {
    if (this.timer !== null) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    this.waiting.clear();
    this.whileHidden.clear();
  }

  private flush(): void {
    this.timer = null;
    const keys = [...this.waiting.entries()];
    this.waiting.clear();
    const isVisible = this.isVisible();
    for (const [hash, key] of keys) {
      const isAlwaysFresh = this.alwaysFresh.some((fresh) => startsWithKey(key, fresh));
      if (!isVisible && !isAlwaysFresh) {
        this.whileHidden.set(hash, key);
      }
      this.invalidate(key, { refetchActive: isVisible || isAlwaysFresh });
    }
  }
}
