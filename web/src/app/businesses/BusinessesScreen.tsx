"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useNiches } from "@/api/catalog";
import type { BusinessView, CurrentUserView } from "@/api/types";
import { BusinessStatusBadge, MemberRoleBadge } from "@/components/business/BusinessStatusBadge";
import { IconBuilding, IconChevronRight, IconPlus } from "@/components/icons";
import { Button, Card, EmptyState, Modal, PageHeader } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryFlag, countryName } from "@/lib/countries";
import { businessPath } from "@/lib/navigation";

import { CreateBusinessForm } from "./CreateBusinessForm";

export function BusinessesScreen({ me, businesses }: { me: CurrentUserView; businesses: BusinessView[] }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const niches = useNiches();
  const [isCreating, setCreating] = useState(businesses.length === 0 && (me.memberships ?? []).length === 0);
  // Remounts the form after each creation.
  const [formKey, setFormKey] = useState(0);

  const nicheName = (key: string) => niches.data?.niches.find((niche) => niche.key === key)?.name ?? "";

  const openCreate = () => {
    setFormKey((value) => value + 1);
    setCreating(true);
  };

  return (
    <>
      <PageHeader
        title={t("businesses.title")}
        description={t("businesses.subtitle")}
        actions={
          businesses.length > 0 ? (
            <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={openCreate}>
              {t("businesses.create")}
            </Button>
          ) : undefined
        }
      />

      {businesses.length === 0 ? (
        <Card>
          <EmptyState
            icon={<IconBuilding className="size-6" />}
            title={t("businesses.emptyTitle")}
            description={t("businesses.emptyDescription")}
            action={
              <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={openCreate}>
                {t("businesses.create")}
              </Button>
            }
          />
        </Card>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {businesses.map((business) => (
            <li key={business.id}>
              <Link
                href={businessPath(business.id)}
                className="group motion-lift flex h-full flex-col rounded-2xl border border-line bg-surface p-5 hover:border-line-strong hover:bg-surface-muted/40"
              >
                <div className="flex items-start justify-between gap-3">
                  <h2 className="min-w-0 text-base font-semibold break-words text-ink">{business.name}</h2>
                  <IconChevronRight className="mt-0.5 size-5 shrink-0 text-ink-subtle group-hover:text-accent" aria-hidden />
                </div>
                <p className="mt-1 text-sm text-ink-muted">
                  {nicheName(business.niche_key) || " "}
                </p>
                <p className="mt-3 text-sm text-ink-muted">
                  <span aria-hidden>{countryFlag(business.country_code)} </span>
                  {[business.city, countryName(business.country_code, locale)].filter(Boolean).join(", ")}
                </p>
                <div className="mt-auto flex flex-wrap gap-2 pt-4">
                  <BusinessStatusBadge status={business.status} />
                  {business.viewer_role ? <MemberRoleBadge role={business.viewer_role} /> : null}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <Modal
        open={isCreating}
        onClose={() => setCreating(false)}
        title={t("businesses.createTitle")}
        description={t("businesses.createDescription")}
        size="lg"
      >
        <CreateBusinessForm
          key={formKey}
          me={me}
          niches={niches}
          onCreated={() => router.refresh()}
          onCancel={() => setCreating(false)}
        />
      </Modal>
    </>
  );
}
