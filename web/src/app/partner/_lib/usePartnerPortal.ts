"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useQuery } from "@/api/useQuery";
import type { Schema } from "@/api/types";

type ReferralPage = Schema<"PartnerReferralPage">;
type CommissionPage = Schema<"CommissionEntryPage">;

/** The signed-in partner's portal: codes, rate and totals (GET /v1/partner). */
export function usePartnerPortal() {
  return useQuery(queryKeys.partner.portal(), () => api.GET("/v1/partner"));
}

/** The businesses the partner's links brought, newest first, a page at a time. */
export function usePartnerReferrals() {
  return useCursorPage<ReferralPage["items"][number], ReferralPage>(queryKeys.partner.referrals(), ({ cursor, limit }) =>
    api.GET("/v1/partner/referrals", { params: { query: { limit: String(limit), cursor: cursor ?? undefined } } }),
  );
}

/** The partner's commission on each paid invoice, newest first, a page at a time. */
export function usePartnerCommissions() {
  return useCursorPage<CommissionPage["items"][number], CommissionPage>(queryKeys.partner.commissions(), ({ cursor, limit }) =>
    api.GET("/v1/partner/commissions", { params: { query: { limit: String(limit), cursor: cursor ?? undefined } } }),
  );
}
