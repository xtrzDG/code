"use client";

/**
 * Settings → Team: whether everyone must sign in with an authenticator app
 * as well as the login code (owners switch it; turning it on needs their
 * own two-factor session), and how many members have no app yet.
 */

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import {
  ButtonLink,
  Card,
  Checkbox,
  InlineError,
  Skeleton,
  useToast,
} from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath, securityPath } from "@/lib/navigation";
import { hasReason } from "@/lib/security/secondFactor";

export function TwoFactorRequirementCard() {
  const { t, tp } = useI18n();
  const toast = useToast();
  const { business, isOwner } = useBusiness();
  const path = { business_id: business.id };
  const security = useQuery(queryKeys.settings.security(business.id), () =>
    api.GET("/v1/businesses/{business_id}/security", { params: { path } }),
  );
  const save = useMutation(
    (required: boolean) =>
      api.PUT("/v1/businesses/{business_id}/security", {
        params: { path },
        body: { require_mfa_for_members: required },
      }),
    { errorToast: false },
  );
  const needsOwnApp = hasReason(save.error, "mfa_required");
  const view = security.data;

  const toggle = async (required: boolean) => {
    const result = await save.run(required);
    if (result.ok) {
      security.setData(result.data);
      toast.success(t("security.team.saved"));
    } else if (!hasReason(result.error, "mfa_required")) {
      toast.error(result.error);
    }
  };

  return (
    <Card
      title={t("security.team.title")}
      description={t("security.team.description")}
    >
      {view ? (
        <div className="space-y-3">
          <Checkbox
            label={t("security.team.toggle")}
            description={
              view.require_mfa_for_members
                ? t("security.team.on")
                : t("security.team.off")
            }
            checked={view.require_mfa_for_members}
            disabled={!isOwner || save.isPending}
            onChange={(event) => void toggle(event.target.checked)}
          />
          <p className="text-sm text-ink-muted">
            {(view.members_without_two_factor ?? 0) > 0
              ? tp(
                  "security.team.without",
                  view.members_without_two_factor ?? 0,
                )
              : t("security.team.everyone")}
          </p>
          {!isOwner ? (
            <p className="text-sm text-ink-subtle">
              {t("security.team.ownerOnly")}
            </p>
          ) : null}
          {needsOwnApp ? (
            <div className="space-y-2 rounded-xl border border-warning/30 bg-warning-soft p-3 text-sm text-warning">
              <p>{t("security.team.ownFirst")}</p>
              <ButtonLink
                href={securityPath({
                  next: businessPath(business.id, "settings/team"),
                })}
                size="sm"
                variant="secondary"
              >
                {t("security.team.openSecurity")}
              </ButtonLink>
            </div>
          ) : null}
        </div>
      ) : security.error ? (
        <InlineError error={security.error} />
      ) : (
        <Skeleton className="h-16 w-full" />
      )}
    </Card>
  );
}
