"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";

import { SectionTabs } from "@/components/content/SectionTabs";
import { IconArrowLeft } from "@/components/icons";
import { Badge, Card, ErrorState, LoadingRegion, OverflowMenu, PageHeader, SkeletonCard, SkeletonPageHeader } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { brandPath, BRANDS_PATH } from "@/lib/navigation";

import { useBrand } from "../_lib/useBrands";
import { BrandFrameContext } from "./BrandFrameContext";
import { DeleteBrandDialog, RenameBrandModal } from "./BrandManageDialogs";

/**
 * A brand's header (name, the person's role, an owner's rename and
 * delete) and tabs; the pages inside read the brand from the frame.
 */
export function BrandFrame({ brandId, children }: { brandId: string; children: ReactNode }) {
  const { t } = useI18n();
  const brand = useBrand(brandId);
  const [dialog, setDialog] = useState<"rename" | "delete" | null>(null);

  const back = (
    <Link href={BRANDS_PATH} className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-ink-muted hover:text-ink">
      <IconArrowLeft className="size-4 rtl:-scale-x-100" aria-hidden />
      {t("brands.back")}
    </Link>
  );
  if (brand.error && !brand.data) {
    return (
      <>
        {back}
        <Card>
          <ErrorState error={brand.error} onRetry={brand.reload} />
        </Card>
      </>
    );
  }
  if (!brand.data) {
    return (
      <LoadingRegion label={t("brands.loading")}>
        <SkeletonPageHeader />
        <div className="space-y-6">
          <SkeletonCard lines={3} />
          <SkeletonCard lines={4} />
        </div>
      </LoadingRegion>
    );
  }

  const view = brand.data;
  const isOwner = view.viewer_role === "brand_owner";
  const tabs = [
    { href: brandPath(view.id), label: t("brands.tabs.overview"), exact: true },
    ...(isOwner ? [{ href: brandPath(view.id, "team"), label: t("brands.tabs.team") }] : []),
    { href: brandPath(view.id, "knowledge"), label: t("brands.tabs.knowledge") },
  ];
  const manage = isOwner ? (
    <OverflowMenu
      label={t("brands.manage.menu")}
      placement="bottom"
      actions={[
        { key: "rename", label: t("brands.manage.rename"), onSelect: () => setDialog("rename") },
        { key: "delete", label: t("brands.manage.deleteBrand"), onSelect: () => setDialog("delete"), tone: "danger" },
      ]}
    />
  ) : undefined;

  return (
    <BrandFrameContext.Provider value={{ brand: view, isOwner }}>
      {back}
      <PageHeader
        eyebrow={<Badge tone={isOwner ? "accent" : "neutral"}>{t(`brands.roles.${view.viewer_role}`)}</Badge>}
        title={<span data-user-content>{view.name}</span>}
        description={t(`brands.roleDescriptions.${view.viewer_role}`)}
        actions={manage}
      />
      <SectionTabs label={view.name} tabs={tabs} className="mb-6" />
      {children}
      {isOwner ? (
        <>
          <RenameBrandModal brand={view} open={dialog === "rename"} onClose={() => setDialog(null)} />
          <DeleteBrandDialog brand={view} open={dialog === "delete"} onClose={() => setDialog(null)} />
        </>
      ) : null}
    </BrandFrameContext.Provider>
  );
}
