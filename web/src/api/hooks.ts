"use client";

/**
 * Data hooks for Client Components on top of the typed `api` client.
 *
 * Reading:
 *
 *     const bookings = useApiQuery(
 *       () => api.GET("/v1/businesses/{business_id}/bookings", {
 *         params: { path: { business_id: businessId } },
 *       }),
 *       [businessId],
 *     );
 *     if (bookings.isLoading) return <Spinner />;
 *     if (bookings.error) return <ErrorState error={bookings.error} onRetry={bookings.reload} />;
 *
 * Writing (errors are shown as localized toasts unless `errorToast: false`):
 *
 *     const save = useApiMutation((body: Body) => api.PATCH("/v1/me", { body }));
 *     const result = await save.run(body);
 *     if (result.ok) { ... result.data ... }
 */

import {
  useCallback,
  useEffect,
  useEffectEvent,
  useRef,
  useState,
  type DependencyList,
} from "react";

import { useToast } from "@/components/ui/Toast";

import { toApiError, type ApiError, type ErrorMessageOverrides } from "./errors";
import { unwrap, type ApiResult } from "./result";

export interface ApiQuery<T> {
  /** Last loaded data; kept while reloading and after a failed reload. */
  data: T | undefined;
  error: ApiError | null;
  /** True until the data for the current dependencies has arrived. */
  isLoading: boolean;
  /** Load again with the same dependencies. */
  reload: () => void;
  /** Replace the data locally (after a mutation that returned it). */
  setData: (update: T | ((current: T | undefined) => T)) => void;
}

interface QueryState<T> {
  key: readonly unknown[];
  data: T | undefined;
  error: ApiError | null;
}

function sameKey(left: readonly unknown[], right: readonly unknown[]): boolean {
  return left.length === right.length && left.every((value, index) => Object.is(value, right[index]));
}

export function useApiQuery<T>(
  fetcher: () => Promise<ApiResult<T>>,
  deps: DependencyList,
  options: { enabled?: boolean } = {},
): ApiQuery<T> {
  const enabled = options.enabled ?? true;
  const [generation, setGeneration] = useState(0);
  const [state, setState] = useState<QueryState<T> | null>(null);
  const key = [...deps, generation];

  const load = useEffectEvent(() => unwrap(fetcher()));

  useEffect(() => {
    if (!enabled) {
      return;
    }
    let active = true;
    const requestKey = [...deps, generation];
    load().then(
      (data) => {
        if (active) {
          setState({ key: requestKey, data, error: null });
        }
      },
      (error: unknown) => {
        if (active) {
          setState((previous) => ({ key: requestKey, data: previous?.data, error: toApiError(error) }));
        }
      },
    );
    return () => {
      active = false;
    };
    // The caller's dependency list drives reloading, as with useEffect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, generation, enabled]);

  const reload = useCallback(() => setGeneration((value) => value + 1), []);
  const setData = useCallback((update: T | ((current: T | undefined) => T)) => {
    setState((previous) => {
      const current = previous?.data;
      const data =
        typeof update === "function" ? (update as (current: T | undefined) => T)(current) : update;
      return { key: previous?.key ?? [], data, error: null };
    });
  }, []);

  const isCurrent = state !== null && sameKey(state.key, key);
  return {
    data: state?.data,
    error: isCurrent ? state.error : null,
    isLoading: enabled && !isCurrent,
    reload,
    setData,
  };
}

export type MutationResult<T> = { ok: true; data: T } | { ok: false; error: ApiError };

export interface ApiMutation<Args extends unknown[], T> {
  run: (...args: Args) => Promise<MutationResult<T>>;
  isPending: boolean;
  error: ApiError | null;
}

export function useApiMutation<Args extends unknown[], T>(
  mutation: (...args: Args) => Promise<ApiResult<T>>,
  options: {
    /** Show failures as a toast (default) or let the caller render them. */
    errorToast?: boolean;
    /** Context-specific texts for some error codes. */
    errorMessages?: ErrorMessageOverrides;
  } = {},
): ApiMutation<Args, T> {
  const toast = useToast();
  const [pendingCount, setPendingCount] = useState(0);
  const [error, setError] = useState<ApiError | null>(null);
  const mutationRef = useRef(mutation);
  const optionsRef = useRef(options);

  useEffect(() => {
    mutationRef.current = mutation;
    optionsRef.current = options;
  });

  const run = useCallback(
    async (...args: Args): Promise<MutationResult<T>> => {
      setPendingCount((count) => count + 1);
      setError(null);
      try {
        const data = await unwrap(mutationRef.current(...args));
        return { ok: true, data };
      } catch (caught) {
        const apiError = toApiError(caught);
        setError(apiError);
        if (optionsRef.current.errorToast ?? true) {
          toast.error(apiError, optionsRef.current.errorMessages);
        }
        return { ok: false, error: apiError };
      } finally {
        setPendingCount((count) => count - 1);
      }
    },
    [toast],
  );

  return { run, isPending: pendingCount > 0, error };
}
