"use client";

/**
 * Writing through the API, with the cache kept in step:
 *
 *     const setStatus = useMutation(
 *       (lead: Lead, status: LeadStatus) => api.PATCH(…, { body: { status } }),
 *       {
 *         // Applied at once; undone if the API refuses.
 *         optimistic: (lead, status) => queryCache.update(queryKeys.leads.all(businessId), …),
 *         // Loaded again after the call settles (the ones on screen right away).
 *         invalidate: [queryKeys.dashboard.all(businessId)],
 *       },
 *     );
 *     const result = await setStatus.run(lead, "won");   // { ok: true, data } | { ok: false, error }
 *
 * Failures are shown as localized toasts unless `errorToast: false`.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { useToast } from "@/components/ui/Toast";

import type { ApiError } from "./errors";
import { executeMutation, type MutationOptions, type MutationResult } from "./mutations";
import type { ApiResult } from "./result";

export type { MutationOptions, MutationResult } from "./mutations";

export interface Mutation<Args extends unknown[], T> {
  run: (...args: Args) => Promise<MutationResult<T>>;
  isPending: boolean;
  error: ApiError | null;
}

export function useMutation<Args extends unknown[], T>(
  mutation: (...args: Args) => Promise<ApiResult<T>>,
  options: MutationOptions<Args, T> = {},
): Mutation<Args, T> {
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
      const current = optionsRef.current;
      setPendingCount((count) => count + 1);
      setError(null);
      try {
        const result = await executeMutation(mutationRef.current, current, args);
        if (!result.ok) {
          setError(result.error);
          if (current.errorToast ?? true) {
            toast.error(result.error, current.errorMessages, current.reasonMessages);
          }
        }
        return result;
      } finally {
        setPendingCount((count) => count - 1);
      }
    },
    [toast],
  );

  return { run, isPending: pendingCount > 0, error };
}
