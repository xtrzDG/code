"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { HOME_PATH } from "@/lib/navigation";

import { memberLabel, ROLE_NAMES, type BusinessMember, type MemberRole } from "./team";

export interface RoleChange {
  member: BusinessMember;
  role: MemberRole;
}

/**
 * The team as the Team tab shows it: members, inviting, changing a role and
 * removing a member (both confirmed first). Removing yourself leaves the
 * business.
 */
export function useTeam() {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business, me } = useBusiness();
  const [members, setMembers] = useState<BusinessMember[]>(business.members);
  const [isInviting, setInviting] = useState(false);
  const [removing, setRemoving] = useState<BusinessMember | null>(null);
  const [removeError, setRemoveError] = useState<ApiError | null>(null);
  const [roleChange, setRoleChange] = useState<RoleChange | null>(null);
  const [roleError, setRoleError] = useState<ApiError | null>(null);

  const changeRole = useMutation(
    (change: RoleChange) =>
      api.PATCH("/v1/businesses/{business_id}/members/{user_id}", {
        params: { path: { business_id: business.id, user_id: change.member.user_id } },
        body: { role: change.role },
      }),
    { errorToast: false },
  );

  const onChangeRole = async () => {
    if (!roleChange) {
      return;
    }
    const result = await changeRole.run(roleChange);
    if (!result.ok) {
      setRoleError(result.error);
      return;
    }
    // The member's name is user content.
    toast.success({
      text: t("settings.roles.changed", { role: t(ROLE_NAMES[roleChange.role]) }),
      values: { name: memberLabel(roleChange.member) },
    });
    setMembers(result.data.members);
    setRoleChange(null);
    // The layout knows the viewer's role; it changes when owners demote themselves.
    router.refresh();
  };

  const remove = useMutation(
    (userId: string) =>
      api.DELETE("/v1/businesses/{business_id}/members/{user_id}", {
        params: { path: { business_id: business.id, user_id: userId } },
      }),
    { errorToast: false },
  );

  const onRemove = async () => {
    if (!removing) {
      return;
    }
    const result = await remove.run(removing.user_id);
    if (!result.ok) {
      setRemoveError(result.error);
      return;
    }
    toast.success({ text: t("settings.team.removed"), values: { name: memberLabel(removing) } });
    setRemoving(null);
    if (removing.user_id === me.user.id) {
      router.replace(HOME_PATH);
      return;
    }
    // The API answers 204: drop the member here, the refresh brings the rest.
    const removedId = removing.user_id;
    setMembers((current) => current.filter((member) => member.user_id !== removedId));
    router.refresh();
  };

  const onInvited = (updated: BusinessMember[], name: string) => {
    setMembers(updated);
    setInviting(false);
    router.refresh();
    toast.success({ text: t("settings.team.invited"), values: { name } });
  };

  return {
    members,
    isInviting,
    setInviting,
    onInvited,
    roleChange,
    askRoleChange: (member: BusinessMember, role: MemberRole) => {
      setRoleError(null);
      setRoleChange({ member, role });
    },
    cancelRoleChange: () => setRoleChange(null),
    roleError,
    isChangingRole: changeRole.isPending,
    onChangeRole,
    removing,
    askRemove: (member: BusinessMember) => {
      setRemoveError(null);
      setRemoving(member);
    },
    cancelRemove: () => setRemoving(null),
    removeError,
    isRemoving: remove.isPending,
    onRemove,
  };
}
