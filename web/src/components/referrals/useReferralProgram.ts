"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";

/**
 * The business's own invitation (owners: GET /v1/businesses/{id}/referrals)
 * and the "Powered by" choice (PUT …/referrals/powered-by, Plus only).
 * The first read claims the business's code.
 */
export function useReferralProgram(businessId: string, { enabled = true }: { enabled?: boolean } = {}) {
  const program = useQuery(
    queryKeys.referrals.program(businessId),
    () => api.GET("/v1/businesses/{business_id}/referrals", { params: { path: { business_id: businessId } } }),
    { enabled },
  );
  const { setData } = program;
  const poweredByChange = useMutation(
    (isHidden: boolean) =>
      api.PUT("/v1/businesses/{business_id}/referrals/powered-by", {
        params: { path: { business_id: businessId } },
        body: { is_hidden: isHidden },
      }),
    { reasonMessages: { plan_required: () => ({ key: "referrals.poweredBy.plusOnly" }) } },
  );

  /** Show or hide the "Powered by" link; true when it went through. */
  const setPoweredByHidden = async (isHidden: boolean): Promise<boolean> => {
    const result = await poweredByChange.run(isHidden);
    if (result.ok) {
      setData((current) => (current ? { ...current, powered_by: result.data } : current));
    }
    return result.ok;
  };

  return { program, setPoweredByHidden, poweredByChange };
}
