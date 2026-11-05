"use client";

import { useEffect } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";

import { SYSTEM_POLL_MS } from "./system";

/**
 * The platform's health (GET /v1/admin/system), looked at again every 30
 * seconds while the page is visible: on call, the page stays open.
 */
export function useAdminSystem() {
  const system = useQuery(queryKeys.admin.system(), () => api.GET("/v1/admin/system"), { staleMs: 0 });
  const { reload } = system;

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        reload();
      }
    }, SYSTEM_POLL_MS);
    return () => window.clearInterval(timer);
  }, [reload]);

  return system;
}
