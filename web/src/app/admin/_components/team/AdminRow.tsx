"use client";

/** One member of the admin team: who, how they sign in, their role, "Remove". */

import type { PlatformAdminRole, PlatformAdminView } from "@/api/types";
import { useViewerFormat } from "@/components/time/ViewerTimeZone";
import { Badge, Button, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { ADMIN_ROLES, ROLE_LABELS, adminDestination } from "../../_lib/team";

export function AdminRow({
  admin,
  isLastSuper,
  isChanging,
  onRoleChange,
  onRemove,
}: {
  admin: PlatformAdminView;
  isLastSuper: boolean;
  isChanging: boolean;
  onRoleChange: (admin: PlatformAdminView, role: PlatformAdminRole) => void;
  onRemove: (admin: PlatformAdminView) => void;
}) {
  const { t } = useI18n();
  const viewer = useViewerFormat();
  const destination = adminDestination(admin);
  const name = admin.display_name ?? destination;
  const date = viewer.date(admin.created_at);
  const addedLine = (member: PlatformAdminView, when: string) =>
    !member.added_by
      ? t("adminTeam.bootstrapped", { date: when })
      : member.added_by_name
        ? t("adminTeam.addedBy", { name: member.added_by_name, date: when })
        : t("adminTeam.addedOn", { date: when });

  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-3 py-4 first:pt-0 last:pb-0">
      <div className="min-w-0 flex-1 space-y-1">
        <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
          <span className="break-all" dir="auto">
            {name}
          </span>
          {admin.is_you ? <Badge tone="accent">{t("adminTeam.you")}</Badge> : null}
        </p>
        {admin.display_name ? <p className="break-all text-sm text-ink-muted">{destination}</p> : null}
        <p className="text-xs text-ink-subtle">
          {[
            admin.user_id ? null : t("adminTeam.notSignedIn"),
            addedLine(admin, date),
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>
      <div className="flex w-full items-center gap-2 sm:w-auto">
        <Select
          aria-label={t("adminTeam.roleFor", { name })}
          value={admin.role}
          disabled={isLastSuper || isChanging}
          onChange={(event) => onRoleChange(admin, event.target.value as PlatformAdminRole)}
          className="min-w-0 flex-1 sm:w-56"
        >
          {ADMIN_ROLES.map((role) => (
            <option key={role} value={role}>
              {t(ROLE_LABELS[role])}
            </option>
          ))}
        </Select>
        <Button
          variant="ghost"
          size="sm"
          disabled={isLastSuper}
          aria-label={t("adminTeam.removeLabel", { name })}
          onClick={() => onRemove(admin)}
        >
          {t("adminTeam.remove")}
        </Button>
      </div>
    </li>
  );
}
