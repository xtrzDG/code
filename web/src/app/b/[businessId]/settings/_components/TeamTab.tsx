"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconPlus } from "@/components/icons";
import { Button, Card } from "@/components/ui";
import { ConfirmDialog, UserSentence } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { memberLabel, sortMembers } from "../_lib/team";
import { useTeam } from "../_lib/useTeam";
import { InviteModal } from "./team/InviteModal";
import { MemberRow } from "./team/MemberRow";

/**
 * Team members with roles. Owners invite staff or other owners by phone or
 * e-mail, change roles and remove members; the last owner stays an owner.
 */
export function TeamTab() {
  const { t } = useI18n();
  const { me, isOwner } = useBusiness();
  const team = useTeam();
  const { members, roleChange, removing } = team;
  const sorted = sortMembers(members);

  return (
    <Card
      title={t("settings.team.title")}
      description={t("settings.team.description")}
      padded={false}
      actions={
        isOwner ? (
          <Button size="sm" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => team.setInviting(true)}>
            {t("settings.team.invite")}
          </Button>
        ) : undefined
      }
    >
      <ul className="divide-y divide-line">
        {sorted.map((member) => (
          <MemberRow
            key={member.user_id}
            member={member}
            members={members}
            onChangeRole={(role) => team.askRoleChange(member, role)}
            onRemove={() => team.askRemove(member)}
          />
        ))}
      </ul>

      <InviteModal open={team.isInviting} onClose={() => team.setInviting(false)} onInvited={team.onInvited} />

      <ConfirmDialog
        open={roleChange !== null}
        onClose={team.cancelRoleChange}
        onConfirm={team.onChangeRole}
        tone={roleChange?.role === "owner" ? "primary" : "danger"}
        isPending={team.isChangingRole}
        error={team.roleError}
        errorOverrides={{ conflict: "settings.roles.lastOwner" }}
        title={
          roleChange
            ? t(roleChange.role === "owner" ? "settings.roles.makeOwnerTitle" : "settings.roles.makeStaffTitle", {
                name: memberLabel(roleChange.member),
              })
            : ""
        }
        confirmLabel={roleChange?.role === "owner" ? t("settings.roles.makeOwner") : t("settings.roles.makeStaff")}
      >
        {roleChange ? (
          <p>
            {roleChange.role === "owner"
              ? t("settings.roles.makeOwnerDescription")
              : roleChange.member.user_id === me.user.id
                ? t("settings.roles.makeSelfStaffDescription")
                : t("settings.roles.makeStaffDescription")}
          </p>
        ) : null}
      </ConfirmDialog>

      <ConfirmDialog
        open={removing !== null}
        onClose={team.cancelRemove}
        onConfirm={team.onRemove}
        isPending={team.isRemoving}
        error={team.removeError}
        title={removing ? <UserSentence text={t("settings.team.removeTitle")} values={{ name: memberLabel(removing) }} /> : ""}
        confirmLabel={t("settings.team.remove")}
      >
        {removing ? (
          <p>{removing.user_id === me.user.id ? t("settings.team.removeSelfDescription") : t("settings.team.removeDescription")}</p>
        ) : null}
      </ConfirmDialog>
    </Card>
  );
}
