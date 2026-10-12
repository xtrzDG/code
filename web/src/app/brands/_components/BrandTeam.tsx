"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { IconPlus } from "@/components/icons";
import { Badge, Button, Card, ConfirmDialog, UserSentence, useToast } from "@/components/ui";
import { OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { useI18n } from "@/i18n/client";
import { formatPhone } from "@/lib/phone";
import { BRANDS_PATH } from "@/lib/navigation";

import { brandMemberLabel, type BrandMemberView } from "../_lib/brands";
import { useBrandTeam } from "../_lib/useBrands";
import { BrandInviteModal } from "./BrandInviteModal";
import { useBrandsContext } from "./BrandsContext";
import { useBrandFrame } from "./BrandFrameContext";
import { MemberRoleModal } from "./MemberRoleModal";

/**
 * The brand's team (brand owners): invite, change a role or the locations
 * a regional manager runs, remove someone or leave. Access through the
 * brand ends at the member's next request.
 */
export function BrandTeam() {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { brand, isOwner } = useBrandFrame();
  const { userId } = useBrandsContext();
  const { remove } = useBrandTeam(brand.id);
  const [isInviting, setInviting] = useState(false);
  const [editing, setEditing] = useState<BrandMemberView | null>(null);
  const [removing, setRemoving] = useState<BrandMemberView | null>(null);

  if (!isOwner) {
    return <OwnerOnlyState />;
  }
  const members = brand.members ?? [];
  const locations = brand.locations ?? [];
  const locationName = (businessId: string) => locations.find((location) => location.business_id === businessId)?.name ?? "";
  const isLeaving = removing?.user_id === userId;

  const onRemove = async () => {
    if (!removing) {
      return;
    }
    const result = await remove.run(removing.user_id);
    if (!result.ok) {
      return;
    }
    toast.success({ text: t("brands.team.removed"), values: { name: brandMemberLabel(removing) } });
    setRemoving(null);
    if (isLeaving) {
      router.push(BRANDS_PATH);
      router.refresh();
    }
  };

  return (
    <Card
      title={t("brands.team.title")}
      description={t("brands.team.description")}
      actions={
        <Button size="sm" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setInviting(true)} aria-haspopup="dialog">
          {t("brands.team.invite")}
        </Button>
      }
    >
      <ul className="divide-y divide-line">
        {members.map((member) => {
          const isSelf = member.user_id === userId;
          const contact = member.phone_number ? formatPhone(member.phone_number) : member.email;
          const places = (member.business_ids ?? []).map(locationName).filter(Boolean).join(" · ");
          return (
            <li key={member.user_id} className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center">
              <div className="min-w-0 flex-1">
                <p className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-sm font-medium text-ink" data-user-content>
                    {brandMemberLabel(member)}
                  </span>
                  {isSelf ? <Badge tone="info">{t("brands.team.you")}</Badge> : null}
                  {member.is_verified ? null : <Badge tone="warning">{t("brands.team.unverified")}</Badge>}
                </p>
                {member.display_name && contact ? (
                  <p className="truncate text-xs text-ink-subtle" dir="ltr" data-user-content>
                    {contact}
                  </p>
                ) : null}
                {member.role === "regional_manager" && places ? (
                  <p className="mt-1 text-xs text-ink-muted" data-user-content>
                    {places}
                  </p>
                ) : null}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={member.role === "brand_owner" ? "accent" : "neutral"}>{t(`brands.roles.${member.role}`)}</Badge>
                <Button variant="ghost" size="sm" onClick={() => setEditing(member)} aria-haspopup="dialog">
                  {t("brands.team.edit")}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setRemoving(member)} aria-haspopup="dialog">
                  {isSelf ? t("brands.team.leave") : t("brands.team.remove")}
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
      <BrandInviteModal open={isInviting} onClose={() => setInviting(false)} brandId={brand.id} locations={locations} />
      <MemberRoleModal member={editing} onClose={() => setEditing(null)} brandId={brand.id} locations={locations} />
      <ConfirmDialog
        open={removing !== null}
        onClose={() => setRemoving(null)}
        onConfirm={onRemove}
        title={removing ? <UserSentence text={t("brands.team.removeTitle")} values={{ name: brandMemberLabel(removing) }} /> : ""}
        description={isLeaving ? t("brands.team.leaveDescription") : t("brands.team.removeDescription")}
        confirmLabel={isLeaving ? t("brands.team.leave") : t("brands.team.remove")}
        isPending={remove.isPending}
        error={remove.error}
        errorOverrides={{ conflict: "brands.team.errors.lastOwner" }}
      />
    </Card>
  );
}
