"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Schema } from "@/api/types";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";

export type CampaignHold = Schema<"CampaignHoldView">;

/**
 * The campaigns held over their opt-out rate (GET /v1/admin/campaign-holds,
 * admins who see operations) and releasing one with a reason (POST
 * …/{business_id}/release, SUPER admins, audited in the client's log; a
 * step-up the API asks for is handled by the API client). A refusal stays
 * in the dialog.
 */
export function useCampaignHolds() {
  const holds = useQuery(
    queryKeys.admin.campaignHolds(),
    () => api.GET("/v1/admin/campaign-holds"),
    {
      staleMs: 60_000,
    },
  );
  const release = useMutation(
    (businessId: string, reason: string) =>
      api.POST("/v1/admin/campaign-holds/{business_id}/release", {
        params: { path: { business_id: businessId } },
        body: { reason },
      }),
    {
      errorToast: false,
      invalidate: [queryKeys.admin.campaignHolds()],
    },
  );

  /** True once the campaign may write again. */
  const releaseHold = async (
    businessId: string,
    reason: string,
  ): Promise<boolean> => {
    const result = await release.run(businessId, reason);
    return result.ok;
  };

  return {
    holds,
    releaseHold,
    isReleasing: release.isPending,
    releaseError: release.error,
  };
}
