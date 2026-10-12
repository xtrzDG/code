"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { IconCopy, IconPlus } from "@/components/icons";
import { Badge, Button, Card, ConfirmDialog, UserSentence, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryFlag } from "@/lib/countries";

import { ownedFreeBusinesses, type BrandLocationView } from "../_lib/brands";
import { useBrandSettings } from "../_lib/useBrands";
import { useBrandsContext } from "./BrandsContext";
import { useBrandFrame } from "./BrandFrameContext";
import { AddLocationModal, CloneLocationModal } from "./LocationModals";

/**
 * The brand's locations (brand owners): add a business they own, make a
 * new location from an existing one, or take one out of the brand.
 */
export function BrandLocations() {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { brand } = useBrandFrame();
  const { memberships } = useBrandsContext();
  const { removeLocation } = useBrandSettings(brand.id);
  const [dialog, setDialog] = useState<"add" | "clone" | null>(null);
  const [removing, setRemoving] = useState<BrandLocationView | null>(null);
  const locations = brand.locations ?? [];
  const candidates = ownedFreeBusinesses(memberships);

  const onRemove = async () => {
    if (!removing) {
      return;
    }
    const result = await removeLocation.run(removing.business_id);
    if (result.ok) {
      toast.success({ text: t("brands.locations.removed"), values: { name: removing.name } });
      setRemoving(null);
      router.refresh();
    }
  };

  return (
    <Card
      aria-label={t("brands.locations.title")}
      title={t("brands.locations.title")}
      description={t("brands.locations.description")}
      actions={
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" leadingIcon={<IconCopy className="size-4" aria-hidden />} onClick={() => setDialog("clone")} aria-haspopup="dialog">
            {t("brands.locations.clone")}
          </Button>
          <Button variant="secondary" size="sm" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setDialog("add")} aria-haspopup="dialog">
            {t("brands.locations.add")}
          </Button>
        </div>
      }
    >
      <ul className="divide-y divide-line">
        {locations.map((location) => (
          <li key={location.business_id} className="flex flex-wrap items-center gap-3 py-3 first:pt-0 last:pb-0">
            <span aria-hidden>{countryFlag(location.country_code)}</span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-ink" data-user-content>
                {location.name}
              </span>
              {location.city ? (
                <span className="block truncate text-xs text-ink-subtle" data-user-content>
                  {location.city}
                </span>
              ) : null}
            </span>
            {location.is_primary ? <Badge tone="neutral">{t("brands.locations.primary")}</Badge> : null}
            <Button variant="ghost" size="sm" onClick={() => setRemoving(location)} aria-haspopup="dialog">
              {t("brands.locations.remove")}
            </Button>
          </li>
        ))}
      </ul>
      <AddLocationModal open={dialog === "add"} onClose={() => setDialog(null)} brandId={brand.id} candidates={candidates} />
      <CloneLocationModal open={dialog === "clone"} onClose={() => setDialog(null)} brandId={brand.id} locations={locations} />
      <ConfirmDialog
        open={removing !== null}
        onClose={() => setRemoving(null)}
        onConfirm={onRemove}
        title={removing ? <UserSentence text={t("brands.locations.removeTitle")} values={{ name: removing.name }} /> : ""}
        description={t("brands.locations.removeDescription")}
        confirmLabel={t("brands.locations.remove")}
        isPending={removeLocation.isPending}
        error={removeLocation.error}
      />
    </Card>
  );
}
