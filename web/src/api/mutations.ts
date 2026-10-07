/**
 * The steps of one mutation, apart from React (useMutation.ts wraps them):
 * apply the optimistic change, call the API, undo the change if the call
 * failed, and mark what the server changed as out of date.
 */

import { toApiError, type ApiError, type ErrorMessageOverrides, type ReasonMessages } from "./errors";
import { queryCache as defaultCache, type QueryCache, type Rollback } from "./queryCache";
import type { QueryKey } from "./queryKey";
import { unwrap, type ApiResult } from "./result";

export type MutationResult<T> = { ok: true; data: T } | { ok: false; error: ApiError };

type MutationKeys<Args extends unknown[], T> =
  | readonly QueryKey[]
  | ((data: T | undefined, ...args: Args) => readonly QueryKey[]);

export interface MutationOptions<Args extends unknown[], T> {
  /** Applies the expected result to the cache before the call; returns how to undo it. */
  optimistic?: (...args: Args) => Rollback | void;
  /** Runs after a failure, once the optimistic change is undone (reopen a dialog, say). */
  rollback?: (error: ApiError, ...args: Args) => void;
  /** Keys reloaded after the call settles: the ones on screen at once, the rest when next shown. */
  invalidate?: MutationKeys<Args, T>;
  /**
   * Keys marked out of date without reloading what is on screen (the local
   * change already shows the result; reloading an audited list would add an
   * audit entry for nothing). They reload when next shown.
   */
  stale?: MutationKeys<Args, T>;
  /** Show failures as a toast (default) or let the caller render them. */
  errorToast?: boolean;
  /** Context-specific texts for some error codes. */
  errorMessages?: ErrorMessageOverrides;
  /** Localized texts for refusal reason codes (they win over `errorMessages`). */
  reasonMessages?: ReasonMessages;
}

function resolveKeys<Args extends unknown[], T>(
  keys: MutationKeys<Args, T> | undefined,
  data: T | undefined,
  args: Args,
): readonly QueryKey[] {
  if (keys === undefined) {
    return [];
  }
  return typeof keys === "function" ? keys(data, ...args) : keys;
}

/** Marks the keys of a settled mutation out of date (see MutationOptions). */
function settleKeys<Args extends unknown[], T>(
  options: Pick<MutationOptions<Args, T>, "invalidate" | "stale">,
  data: T | undefined,
  args: Args,
  cache: QueryCache = defaultCache,
): void {
  for (const key of resolveKeys(options.stale, data, args)) {
    cache.invalidate(key, { refetchActive: false });
  }
  for (const key of resolveKeys(options.invalidate, data, args)) {
    cache.invalidate(key);
  }
}

/** Runs one mutation: optimistic change, call, rollback on failure, invalidation. */
export async function executeMutation<Args extends unknown[], T>(
  mutation: (...args: Args) => Promise<ApiResult<T>>,
  options: MutationOptions<Args, T>,
  args: Args,
  cache: QueryCache = defaultCache,
): Promise<MutationResult<T>> {
  const undo = options.optimistic?.(...args);
  try {
    const data = await unwrap(mutation(...args));
    settleKeys(options, data, args, cache);
    return { ok: true, data };
  } catch (caught) {
    const error = toApiError(caught);
    if (typeof undo === "function") {
      undo();
    }
    options.rollback?.(error, ...args);
    settleKeys(options, undefined, args, cache);
    return { ok: false, error };
  }
}
