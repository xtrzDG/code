"use client";

import { useState } from "react";

import { api } from "@/api/client";
import type { PagedData } from "@/api/paging";
import { queryCache, type QueryKey } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { LEAD_STATUS } from "@/components/insights/labels";
import type { LeadListItem, LeadPage, LeadStatus } from "@/components/insights/types";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { withLeadStatus, type LeadTab } from "./leadModel";

type LeadList = PagedData<LeadListItem, LeadPage>;

interface StatusChange {
  lead: LeadListItem;
  status: LeadStatus;
  /** The shown list to put back as it was (an Undo). */
  restore?: LeadList;
}

/**
 * Moving a lead to another status: the list changes at once (the lead
 * leaves a tab of its old status, the tab counts follow) and goes back if
 * the API refuses. A done move offers Undo for a few seconds, which moves
 * the lead back on the server and puts the list back as it was.
 */
export function useLeadStatus(listKey: QueryKey, tab: LeadTab) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [pendingIds, setPendingIds] = useState<ReadonlySet<string>>(new Set());

  const mutation = useMutation(
    ({ lead, status }: StatusChange) =>
      api.PATCH("/v1/businesses/{business_id}/leads/{lead_id}", {
        params: { path: { business_id: business.id, lead_id: lead.id } },
        body: { status },
      }),
    {
      optimistic: ({ lead, status, restore }) =>
        queryCache.update<LeadList>(listKey, (data) =>
          restore ?? withLeadStatus(data, lead.id, lead.status, status, tab),
        ),
      // The other tabs and filters reload when shown; the shown list already
      // has the change (reloading it would only add an audit entry).
      stale: [queryKeys.leads.all(business.id)],
      invalidate: [queryKeys.dashboard.all(business.id), queryKeys.inbox.all(business.id)],
    },
  );

  const markPending = (id: string, isPending: boolean) =>
    setPendingIds((current) => {
      const next = new Set(current);
      if (isPending) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });

  const run = async (change: StatusChange) => {
    markPending(change.lead.id, true);
    const result = await mutation.run(change);
    markPending(change.lead.id, false);
    return result.ok;
  };

  const changeStatus = async (lead: LeadListItem, status: LeadStatus) => {
    if (status === lead.status) {
      return;
    }
    const shownBefore = queryCache.get<LeadList>(listKey).data;
    if (!(await run({ lead, status }))) {
      return;
    }
    toast.undoable(t("leads.updated", { status: t(LEAD_STATUS[status].label) }), () => {
      void run({ lead: { ...lead, status }, status: lead.status, restore: shownBefore }).then((isDone) => {
        if (isDone) {
          toast.success(t("leads.updated", { status: t(LEAD_STATUS[lead.status].label) }));
        }
      });
    });
  };

  return { changeStatus, isPending: (leadId: string) => pendingIds.has(leadId) };
}
