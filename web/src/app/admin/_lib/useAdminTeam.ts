"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import type { PlatformAdminRole } from "@/api/types";

import { addAdminBody, type AddAdminBy } from "./team";

/**
 * The admin team (GET /v1/admin/team) and its changes; an answer with the
 * whole team replaces the list. Changes may first ask to confirm with a
 * code (step-up, handled by the API client). Each change resolves to true
 * when it went through.
 */
export function useAdminTeam() {
  const team = useQuery(queryKeys.admin.team(), () => api.GET("/v1/admin/team"));
  const { setData, reload } = team;
  const addition = useMutation(
    (by: AddAdminBy, value: string, role: PlatformAdminRole) =>
      api.POST("/v1/admin/team", { body: addAdminBody(by, value, role) }),
    { errorToast: false },
  );
  const roleChange = useMutation(
    (adminId: string, role: PlatformAdminRole) =>
      api.PATCH("/v1/admin/team/{admin_id}", { params: { path: { admin_id: adminId } }, body: { role } }),
    { errorMessages: { conflict: "adminTeam.lastSuper" } },
  );
  const removal = useMutation(
    (adminId: string) => api.DELETE("/v1/admin/team/{admin_id}", { params: { path: { admin_id: adminId } } }),
    { errorToast: false },
  );

  const add = async (by: AddAdminBy, value: string, role: PlatformAdminRole): Promise<boolean> => {
    const result = await addition.run(by, value, role);
    if (result.ok) {
      setData(result.data);
    }
    return result.ok;
  };

  const changeRole = async (adminId: string, role: PlatformAdminRole): Promise<boolean> => {
    const result = await roleChange.run(adminId, role);
    if (result.ok) {
      setData(result.data);
    }
    return result.ok;
  };

  const remove = async (adminId: string): Promise<boolean> => {
    const result = await removal.run(adminId);
    if (result.ok) {
      reload();
    }
    return result.ok;
  };

  return { team, add, addition, changeRole, roleChange, remove, removal };
}
