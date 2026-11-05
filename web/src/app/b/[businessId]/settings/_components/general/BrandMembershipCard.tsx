"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { Button, ButtonLink, Card, ConfirmDialog, UserSentence, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { brandPath, HOME_PATH } from "@/lib/navigation";

/**
 * The brand this location belongs to (owners): what the brand's team does
 * here, a link to the brand for its team, and taking the location out of
 * the brand. A location's own owners never depend on the brand's team for
 * that; a brand owner who is no member of the location's own team loses
 * access with the rest of the brand's team, so the cabinet then leaves it.
 */
export function BrandMembershipCard() {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business, me, isOwner } = useBusiness();
  const [isConfirming, setConfirming] = useState(false);
  const leave = useMutation(
    () => api.DELETE("/v1/businesses/{business_id}/brand", { params: { path: { business_id: business.id } } }),
    { errorToast: false, invalidate: [queryKeys.brands.all(), queryKeys.knowledge.all(business.id)] },
  );

  if (!business.brand_id || !isOwner) {
    return null;
  }
  const brandName = (me.memberships ?? []).find((membership) => membership.business_id === business.id)?.brand_name ?? null;
  const staysMember = business.members.some((member) => member.user_id === me.user.id);

  const onLeave = async () => {
    const result = await leave.run();
    if (!result.ok) {
      return;
    }
    toast.success(t("brands.location.left"));
    setConfirming(false);
    if (staysMember) {
      router.refresh();
      return;
    }
    router.replace(HOME_PATH);
  };

  return (
    <Card title={t("brands.location.title")} data-testid="brand-membership">
      <div className="space-y-4">
        <div className="space-y-1.5 text-sm">
          <p className="font-medium text-ink">
            {brandName ? (
              <UserSentence text={t("brands.location.named")} values={{ name: brandName }} />
            ) : (
              t("brands.location.unnamed")
            )}
          </p>
          <p className="text-ink-muted">{t("brands.location.description")}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {brandName ? (
            <ButtonLink href={brandPath(business.brand_id)} variant="secondary" size="sm">
              {t("brands.location.open")}
            </ButtonLink>
          ) : null}
          <Button variant="danger-ghost" size="sm" onClick={() => setConfirming(true)} aria-haspopup="dialog">
            {t("brands.location.leave")}
          </Button>
        </div>
      </div>
      <ConfirmDialog
        open={isConfirming}
        onClose={() => setConfirming(false)}
        onConfirm={onLeave}
        title={t("brands.location.leaveTitle")}
        description={
          staysMember
            ? t("brands.location.leaveDescription")
            : `${t("brands.location.leaveDescription")} ${t("brands.location.leaveOwnAccess")}`
        }
        confirmLabel={t("brands.location.leave")}
        isPending={leave.isPending}
        error={leave.error}
      />
    </Card>
  );
}
