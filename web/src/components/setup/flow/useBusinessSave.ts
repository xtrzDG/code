"use client";

/**
 * Saving the business's own settings from the tunnel (its name, city,
 * languages, staff contacts). The business is read fresh and saved with
 * the revision it showed; when someone saved it in between (another
 * owner, a manager linking Telegram), it is read again and the change
 * applied once more on top. The cabinet around follows (router.refresh).
 */

import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/result";
import { invalidate } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import type { BusinessView, RequestBody } from "@/api/types";
import { useToast } from "@/components/ui";
import { describeError, isApiError } from "@/api/errors";
import { useI18n } from "@/i18n/client";

export type BusinessChanges = Omit<RequestBody<"/v1/businesses/{business_id}", "patch">, "expected_revision">;

function isStale(error: unknown): boolean {
  return isApiError(error) && error.reasons.some((reason) => reason.code === "stale_revision");
}

export function useBusinessSave(businessId: string) {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const stored = useQuery(
    queryKeys.business.detail(businessId),
    () => api.GET("/v1/businesses/{business_id}", { params: { path: { business_id: businessId } } }),
    { requireFresh: true },
  );

  const send = useCallback(
    (changes: BusinessChanges, revision: number | undefined) =>
      unwrap(
        api.PATCH("/v1/businesses/{business_id}", {
          params: { path: { business_id: businessId } },
          body: { ...changes, ...(revision === undefined ? {} : { expected_revision: revision }) },
        }),
      ),
    [businessId],
  );

  /** Apply `change` to the business as stored; resolves to the saved business, or null. */
  const save = useCallback(
    async (change: (business: BusinessView) => BusinessChanges): Promise<BusinessView | null> => {
      const read = () => unwrap(api.GET("/v1/businesses/{business_id}", { params: { path: { business_id: businessId } } }));
      try {
        let current = stored.data ?? (await read());
        let saved: BusinessView;
        try {
          saved = await send(change(current), current.revision);
        } catch (error) {
          if (!isStale(error)) {
            throw error;
          }
          current = await read();
          saved = await send(change(current), current.revision);
        }
        stored.setData(saved);
        invalidate(queryKeys.business.all(businessId), { refetchActive: false });
        router.refresh();
        return saved;
      } catch (error) {
        toast.show({ tone: "error", title: describeError(error, t).title });
        return null;
      }
    },
    [businessId, router, send, stored, t, toast],
  );

  return { business: stored.data, isLoading: stored.isLoading, reload: stored.reload, save };
}
