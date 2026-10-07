"use client";

import { useEffect } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { SUPPORT_ACCESS_POLL_MS } from "@/lib/supportAccess";

/**
 * Platform support in this business now (GET …/support-access), asked
 * again every minute, and the owner's and support's actions on it.
 */
export function useSupportAccess(businessId: string) {
  const path = { params: { path: { business_id: businessId } } };
  const access = useQuery(queryKeys.supportAccess.status(businessId), () =>
    api.GET("/v1/businesses/{business_id}/support-access", path),
  );
  const { reload, setData } = access;

  useEffect(() => {
    const timer = window.setInterval(reload, SUPPORT_ACCESS_POLL_MS);
    return () => window.clearInterval(timer);
  }, [reload]);

  const writeAccess = useMutation(
    (isAllowed: boolean, hours: number | null) =>
      api.PUT("/v1/businesses/{business_id}/support-access/write-access", {
        ...path,
        body: { is_allowed: isAllowed, hours },
      }),
  );
  const ending = useMutation(() => api.DELETE("/v1/businesses/{business_id}/support-access", path), {
    errorToast: false,
  });
  const leaving = useMutation(() =>
    api.DELETE("/v1/admin/clients/{business_id}/access", path),
  );

  const setWriteAccess = async (isAllowed: boolean, hours: number | null): Promise<boolean> => {
    const result = await writeAccess.run(isAllowed, hours);
    if (result.ok) {
      setData(result.data);
    }
    return result.ok;
  };

  const end = async (): Promise<boolean> => {
    const result = await ending.run();
    if (result.ok) {
      reload();
    }
    return result.ok;
  };

  const leave = async (): Promise<boolean> => (await leaving.run()).ok;

  return { access, setWriteAccess, writeAccess, end, ending, leave, leaving };
}
