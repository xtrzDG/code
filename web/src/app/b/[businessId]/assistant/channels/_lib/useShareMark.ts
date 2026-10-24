"use client";

import { useCallback } from "react";

import { api } from "@/api/client";
import { invalidate } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useBusiness } from "@/components/business/BusinessContext";

/** The API's share marks (`SetupShareMark`, a path segment). */
export type ShareMark = "printed_qr" | "downloaded_qr";

/**
 * Tells the setup guide that the link went out into the world (a printed
 * table card, a downloaded QR code): the "share" step is done. Quiet and
 * best effort: the print or download itself never waits for it or fails
 * because of it.
 */
export function useShareMark(): (mark: ShareMark) => void {
  const { business } = useBusiness();
  const businessId = business.id;
  return useCallback(
    (mark: ShareMark) => {
      void api
        .POST("/v1/businesses/{business_id}/setup/share-marks/{mark}", {
          params: { path: { business_id: businessId, mark } },
        })
        .then((result) => {
          if (!result.error) {
            invalidate(queryKeys.setup.all(businessId));
          }
        })
        .catch(() => undefined);
    },
    [businessId],
  );
}
