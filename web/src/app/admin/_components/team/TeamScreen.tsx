"use client";

/**
 * /admin/team: the platform admin team, SUPER admins first. Only a SUPER
 * admin manages it (the page is not in the others' navigation and the API
 * refuses them); the last SUPER admin cannot lose the role or leave.
 */

import { useState } from "react";

import type { PlatformAdminRole, PlatformAdminView } from "@/api/types";
import { IconPlus } from "@/components/icons";
import { Button, Card, ConfirmDialog, ErrorState, LoadingRegion, PageHeader, SkeletonCard, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { isLastSuper } from "../../_lib/team";
import { useAdminTeam } from "../../_lib/useAdminTeam";
import { AddAdminDialog } from "./AddAdminDialog";
import { AdminRow } from "./AdminRow";

export function TeamScreen() {
  const { t } = useI18n();
  const toast = useToast();
  const { team, add, addition, changeRole, roleChange, remove, removal } = useAdminTeam();
  const [isAdding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<PlatformAdminView | null>(null);
  const items = team.data?.items ?? [];

  const onAdd = async (by: "phone" | "email", value: string, role: PlatformAdminRole) => {
    if (await add(by, value, role)) {
      setAdding(false);
      toast.success(t("adminTeam.added"));
    }
  };
  const onRoleChange = async (admin: PlatformAdminView, role: PlatformAdminRole) => {
    if (role !== admin.role && (await changeRole(admin.id, role))) {
      toast.success(t("adminTeam.changed"));
    }
  };
  const onRemove = async () => {
    if (removing && (await remove(removing.id))) {
      setRemoving(null);
      toast.success(t("adminTeam.removed"));
    }
  };

  return (
    <>
      <PageHeader
        title={t("adminTeam.title")}
        description={t("adminTeam.description")}
        actions={
          <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setAdding(true)}>
            {t("adminTeam.add")}
          </Button>
        }
      />
      {team.error && !team.data ? (
        <Card>
          <ErrorState error={team.error} onRetry={team.reload} />
        </Card>
      ) : !team.data ? (
        <TeamSkeleton />
      ) : (
        <Card aria-label={t("adminTeam.title")}>
          <ul className="divide-y divide-line">
            {items.map((admin) => (
              <AdminRow
                key={admin.id}
                admin={admin}
                isLastSuper={isLastSuper(admin, items)}
                isChanging={roleChange.isPending}
                onRoleChange={(member, role) => void onRoleChange(member, role)}
                onRemove={setRemoving}
              />
            ))}
          </ul>
        </Card>
      )}

      <AddAdminDialog
        open={isAdding}
        isPending={addition.isPending}
        error={addition.error}
        onClose={() => setAdding(false)}
        onAdd={onAdd}
      />
      <ConfirmDialog
        open={removing !== null}
        onClose={() => setRemoving(null)}
        onConfirm={onRemove}
        isPending={removal.isPending}
        error={removal.error}
        errorOverrides={{ conflict: "adminTeam.lastSuper" }}
        title={t("adminTeam.removeTitle", { name: removing?.display_name ?? removing?.email ?? removing?.phone_number ?? "" })}
        description={t("adminTeam.removeDescription")}
        confirmLabel={t("adminTeam.remove")}
      />
    </>
  );
}

/** The list while the team loads (also the route's loading.tsx). */
export function TeamSkeleton() {
  const { t } = useI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <SkeletonCard lines={5} />
    </LoadingRegion>
  );
}
