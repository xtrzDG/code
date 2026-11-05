"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import type { RequestBody } from "@/api/types";

type PartnerChange = RequestBody<"/v1/admin/partners/{partner_id}", "patch">;

/**
 * The partners (GET /v1/admin/partners) and their changes; every change
 * answers with the partner, which replaces its row. Each change resolves
 * to true when it went through.
 */
export function useAdminPartners() {
  const partners = useQuery(queryKeys.admin.partners(), () => api.GET("/v1/admin/partners"));
  const { setData, reload } = partners;
  const creation = useMutation(
    (body: RequestBody<"/v1/admin/partners", "post">) => api.POST("/v1/admin/partners", { body }),
    { errorToast: false },
  );
  const change = useMutation((partnerId: string, body: PartnerChange) =>
    api.PATCH("/v1/admin/partners/{partner_id}", { params: { path: { partner_id: partnerId } }, body }),
  );
  const codeAddition = useMutation(
    (partnerId: string, code: string) =>
      api.POST("/v1/admin/partners/{partner_id}/codes", { params: { path: { partner_id: partnerId } }, body: { code } }),
    { errorToast: false },
  );

  const replace = (partner: NonNullable<typeof partners.data>["items"][number]) =>
    setData((current) =>
      current ? { ...current, items: current.items.map((item) => (item.partner_id === partner.partner_id ? partner : item)) } : current,
    );

  const create = async (body: RequestBody<"/v1/admin/partners", "post">): Promise<boolean> => {
    const result = await creation.run(body);
    if (result.ok) {
      reload();
    }
    return result.ok;
  };

  const update = async (partnerId: string, body: PartnerChange): Promise<boolean> => {
    const result = await change.run(partnerId, body);
    if (result.ok) {
      replace(result.data);
    }
    return result.ok;
  };

  const addCode = async (partnerId: string, code: string): Promise<boolean> => {
    const result = await codeAddition.run(partnerId, code);
    if (result.ok) {
      replace(result.data);
    }
    return result.ok;
  };

  return { partners, create, creation, update, change, addCode, codeAddition };
}

/** One month's payout report and marking a partner's month paid. */
export function usePayouts(month: string) {
  const report = useQuery(queryKeys.admin.payouts(month), () =>
    api.GET("/v1/admin/partners/payouts", { params: { query: { month } } }),
  );
  const marking = useMutation(
    (partnerId: string, reference: string) =>
      api.POST("/v1/admin/partners/{partner_id}/payouts", {
        params: { path: { partner_id: partnerId } },
        body: { month, reference },
      }),
    { errorToast: false },
  );

  const markPaid = async (partnerId: string, reference: string): Promise<boolean> => {
    const result = await marking.run(partnerId, reference);
    if (result.ok) {
      report.reload();
    }
    return result.ok;
  };

  return { report, markPaid, marking };
}
