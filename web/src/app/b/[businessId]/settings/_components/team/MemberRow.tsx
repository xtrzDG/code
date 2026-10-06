"use client";

import { MemberRoleBadge } from "@/components/business/BusinessStatusBadge";
import { useBusiness } from "@/components/business/BusinessContext";
import { Badge, Button, Select } from "@/components/ui";
import { IconUsers } from "@/components/icons";
import { useI18n } from "@/i18n/client";

import {
  allowedRoles,
  canRemoveMember,
  memberInitials,
  memberLabel,
  ROLE_NAMES,
  type BusinessMember,
  type MemberRole,
} from "../../_lib/team";

/** One member: initials, name and contacts; for owners, the role select and remove. */
export function MemberRow({
  member,
  members,
  onChangeRole,
  onRemove,
}: {
  member: BusinessMember;
  /** The whole team (the last owner cannot be demoted or removed). */
  members: readonly BusinessMember[];
  onChangeRole: (role: MemberRole) => void;
  onRemove: () => void;
}) {
  const { t } = useI18n();
  const { me, isOwner } = useBusiness();
  const name = memberLabel(member);
  const isMe = member.user_id === me.user.id;
  const contacts = [member.phone_number, member.email].filter((value): value is string => Boolean(value) && value !== name);
  const removable = canRemoveMember(member, members);
  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-3 px-5 py-4 sm:px-6">
      <span
        className="flex size-10 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent-ink"
        aria-hidden
        data-user-content
      >
        {memberInitials(member) ?? <IconUsers className="size-5" />}
      </span>
      <div className="min-w-0 flex-1 basis-40">
        <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
          <span dir="auto" data-user-content className="break-all">
            {name}
          </span>
          {isMe ? <Badge tone="info">{t("settings.team.you")}</Badge> : null}
        </p>
        {contacts.length > 0 ? (
          <p className="mt-0.5 truncate text-sm text-ink-muted" dir="ltr">
            {contacts.join(" · ")}
          </p>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {!member.is_verified ? <Badge tone="warning">{t("settings.team.notSignedIn")}</Badge> : null}
        {isOwner ? (
          <Select
            aria-label={t("settings.roles.roleOf", { name })}
            className="w-auto min-w-28"
            value={member.role}
            title={allowedRoles(member, members).length === 1 ? t("settings.roles.lastOwner") : undefined}
            onChange={(event) => {
              const role = event.target.value as MemberRole;
              if (role !== member.role) {
                onChangeRole(role);
              }
            }}
          >
            {(["owner", "staff", "agency"] as const).map((role) => (
              <option key={role} value={role} disabled={!allowedRoles(member, members).includes(role)}>
                {t(ROLE_NAMES[role])}
              </option>
            ))}
          </Select>
        ) : (
          <MemberRoleBadge role={member.role} />
        )}
        {isOwner ? (
          <Button
            variant="danger-ghost"
            size="sm"
            disabled={!removable}
            title={!removable ? t("settings.team.lastOwner") : undefined}
            aria-label={t("settings.team.removeLabel", { name })}
            onClick={onRemove}
          >
            {t("settings.team.remove")}
          </Button>
        ) : null}
      </div>
    </li>
  );
}
