"use client";

/**
 * Where the open business stands on its way out (`GET …/closure`, any
 * member), and keeping it: an owner cancels the closure within its 30 days
 * (`DELETE …/closure`), which brings the channels back. The business itself
 * changed then (its status, its channels), so the page's data is loaded
 * again.
 */

import { useRouter } from "next/navigation";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { useBusiness } from "./BusinessContext";

export function useBusinessClosure() {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const closure = useQuery(queryKeys.closure.detail(business.id), () =>
    api.GET("/v1/businesses/{business_id}/closure", { params: { path } }),
  );
  const cancel = useMutation(() => api.DELETE("/v1/businesses/{business_id}/closure", { params: { path } }), {
    invalidate: [queryKeys.closure.detail(business.id), queryKeys.business.all(business.id)],
  });

  /** Keep the business; true once the closure is cancelled. */
  const keep = async (): Promise<boolean> => {
    const result = await cancel.run();
    if (!result.ok) {
      return false;
    }
    toast.success(t("closure.banner.kept"));
    router.refresh();
    return true;
  };

  return { closure, keep, isKeeping: cancel.isPending, keepError: cancel.error };
}
