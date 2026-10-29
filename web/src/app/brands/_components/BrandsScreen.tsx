"use client";

import Link from "next/link";
import { useState } from "react";

import { IconBuilding, IconChevronRight, IconPlus } from "@/components/icons";
import { Badge, Button, Card, EmptyState, ErrorState, LoadingRegion, PageHeader, SkeletonCard } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { brandPath } from "@/lib/navigation";

import { ownedFreeBusinesses, type BrandView } from "../_lib/brands";
import { useMyBrands } from "../_lib/useBrands";
import { useBrandsContext } from "./BrandsContext";
import { CreateBrandModal } from "./CreateBrandModal";

/**
 * The brands the person belongs to, each opening its overview, and "Create
 * a brand" from a business they own that is in no brand yet.
 */
export function BrandsScreen() {
  const { t } = useI18n();
  const { memberships } = useBrandsContext();
  const brands = useMyBrands();
  const [isCreating, setCreating] = useState(false);
  const candidates = ownedFreeBusinesses(memberships);
  const create =
    candidates.length > 0 ? (
      <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setCreating(true)} aria-haspopup="dialog">
        {t("brands.create.title")}
      </Button>
    ) : undefined;

  if (brands.error && !brands.data) {
    return (
      <Card>
        <ErrorState error={brands.error} onRetry={brands.reload} />
      </Card>
    );
  }
  if (!brands.data) {
    return <BrandsSkeleton />;
  }
  return (
    <>
      <PageHeader title={t("brands.title")} description={t("brands.description")} actions={brands.data.length > 0 ? create : undefined} />
      {brands.data.length === 0 ? (
        <Card>
          <EmptyState
            icon={<IconBuilding className="size-6" />}
            title={t("brands.empty.title")}
            description={candidates.length > 0 ? t("brands.empty.description") : t("brands.create.noOwnedBusiness")}
            action={create}
          />
        </Card>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {brands.data.map((brand) => (
            <li key={brand.id}>
              <BrandCard brand={brand} />
            </li>
          ))}
        </ul>
      )}
      <CreateBrandModal open={isCreating} onClose={() => setCreating(false)} candidates={candidates} />
    </>
  );
}

function BrandCard({ brand }: { brand: BrandView }) {
  const { t, tp } = useI18n();
  const locations = brand.locations ?? [];
  return (
    <Link
      href={brandPath(brand.id)}
      className="group motion-lift flex h-full flex-col rounded-2xl border border-line bg-surface p-5 hover:border-line-strong hover:bg-surface-muted/40"
    >
      <div className="flex items-start justify-between gap-3">
        <h2 className="min-w-0 text-base font-semibold break-words text-ink" data-user-content>
          {brand.name}
        </h2>
        <IconChevronRight className="mt-0.5 size-5 shrink-0 text-ink-subtle group-hover:text-accent rtl:-scale-x-100" aria-hidden />
      </div>
      <p className="mt-1 text-sm text-ink-muted">{tp("brands.locationCount", locations.length)}</p>
      <p className="mt-2 line-clamp-2 text-sm text-ink-subtle" data-user-content>
        {locations.map((location) => location.name).join(" · ")}
      </p>
      <div className="mt-auto pt-4">
        <Badge tone={brand.viewer_role === "brand_owner" ? "accent" : "neutral"}>{t(`brands.roles.${brand.viewer_role}`)}</Badge>
      </div>
    </Link>
  );
}

/** The list while it loads (also the route's loading.tsx). */
export function BrandsSkeleton() {
  const { t } = useI18n();
  return (
    <LoadingRegion label={t("brands.loading")}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <SkeletonCard lines={3} />
        <SkeletonCard lines={3} />
      </div>
    </LoadingRegion>
  );
}
