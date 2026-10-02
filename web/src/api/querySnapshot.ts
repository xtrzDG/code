/** What the query cache holds for one key, as readers see it. */

import type { ApiError } from "./errors";

export interface QuerySnapshot<T> {
  /** The last data loaded (or written locally); kept while reloading and after a failed reload. */
  readonly data: T | undefined;
  /** The last load failed (cleared by the next success or local write). */
  readonly error: ApiError | null;
  /** When the data last came from the server (ms since epoch); 0 for never. */
  readonly updatedAt: number;
  /** A load is running. */
  readonly isFetching: boolean;
  /** The server changed since the data was loaded: the next reader loads it again. */
  readonly isInvalidated: boolean;
}

/** Undoes a local change (an optimistic update) unless newer data replaced it since. */
export type Rollback = () => void;

export const EMPTY_SNAPSHOT: QuerySnapshot<never> = Object.freeze({
  data: undefined,
  error: null,
  updatedAt: 0,
  isFetching: false,
  isInvalidated: false,
});
