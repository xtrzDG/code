"use client";

import { useState } from "react";

import { api } from "@/api/client";
import type { Schema } from "@/api/types";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { Badge, Button, Card, ConfirmDialog, ErrorState, SkeletonRows, UserContent, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { useClientFormat } from "../../_lib/useClientFormat";

type Member = Schema<"ClientMemberSessionsView">;

/**
 * /admin/clients/[businessId] → "Team sign-ins": each member of the
 * client's team with their role, how many devices they are signed in on
 * and when one was last used (no devices or addresses: those stay the
 * person's own). An admin who may change clients' accounts ends every
 * session of one member, after a confirmation (and the API's step-up).
 */
export function TeamSessionsCard({
  businessId,
  timeZone,
  canEnd,
}: {
  businessId: string;
  timeZone: string;
  canEnd: boolean;
}) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const { dateTime } = useClientFormat(timeZone);
  const key = ["admin", "client", businessId, "members"] as const;
  const members = useQuery(key, () =>
    api.GET("/v1/admin/clients/{business_id}/members", { params: { path: { business_id: businessId } } }),
  );
  const [ending, setEnding] = useState<Member | null>(null);
  const end = useMutation(
    (member: Member) =>
      api.POST("/v1/admin/clients/{business_id}/members/{member_user_id}/sessions/revoke", {
        params: { path: { business_id: businessId, member_user_id: member.user_id } },
      }),
    { invalidate: [key], errorToast: false },
  );
  const nameOf = (member: Member) => member.display_name || member.masked_login || t("adminSessions.unnamed");

  const onEnd = async () => {
    if (!ending) {
      return;
    }
    const result = await end.run(ending);
    if (result.ok) {
      setEnding(null);
      toast.success(tp("adminSessions.ended", result.data.revoked_count));
    }
  };

  return (
    <Card title={t("adminSessions.title")} description={t("adminSessions.description")} aria-label={t("adminSessions.title")}>
      {members.error && !members.data ? (
        <ErrorState error={members.error} onRetry={members.reload} />
      ) : !members.data ? (
        <SkeletonRows rows={2} />
      ) : (
        <ul className="divide-y divide-line">
          {members.data.items.map((member) => (
            <li key={member.user_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div className="min-w-0 space-y-1">
                <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
                  <UserContent>{nameOf(member)}</UserContent>
                  <Badge tone={member.role === "owner" ? "accent" : "neutral"}>{t(`adminSessions.roles.${member.role}`)}</Badge>
                </p>
                <p className="text-sm text-ink-muted">
                  {member.live_session_count > 0
                    ? tp("adminSessions.devices", member.live_session_count)
                    : t("adminSessions.notSignedIn")}
                  {member.last_seen_at ? ` · ${t("adminSessions.lastUsed", { date: dateTime(member.last_seen_at) })}` : null}
                </p>
              </div>
              {canEnd && member.live_session_count > 0 ? (
                <Button
                  variant="secondary"
                  size="sm"
                  aria-label={t("adminSessions.endLabel", { name: nameOf(member) })}
                  onClick={() => setEnding(member)}
                >
                  {t("adminSessions.end")}
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      <ConfirmDialog
        open={ending !== null}
        onClose={() => setEnding(null)}
        onConfirm={onEnd}
        isPending={end.isPending}
        error={end.error}
        title={t("adminSessions.endTitle", { name: ending ? nameOf(ending) : "" })}
        description={t("adminSessions.endDescription", { name: ending ? nameOf(ending) : "" })}
        confirmLabel={t("adminSessions.end")}
      />
    </Card>
  );
}
