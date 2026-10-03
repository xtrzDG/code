"use client";

import Link from "next/link";

import { useNiches } from "@/api/catalog";
import type { BusinessView } from "@/api/types";
import { BusinessStatusBadge, MemberRoleBadge } from "@/components/business/BusinessStatusBadge";
import { IconChevronRight, IconPlus, IconSparkles } from "@/components/icons";
import { ButtonLink, Card, EmptyState, PageHeader } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryFlag, countryName } from "@/lib/countries";
import { businessPath, CREATE_PATH, setupPath } from "@/lib/navigation";

/** An owner's business not live yet (never launched): its card leads back into the tunnel. */
function isBeingSetUp(business: Pick<BusinessView, "status" | "viewer_role">): boolean {
  return business.viewer_role === "owner" && (business.status === "onboarding" || business.status === "testing");
}

/**
 * The businesses the user works in, each opening its cabinet (or, for an
 * owner before its assistant is live, the tunnel where they left off), and
 * "New assistant" leading into the full-screen "Create an AI assistant".
 */

export function BusinessesScreen({ businesses }: { businesses: BusinessView[] }) {
  const { t, locale } = useI18n();
  const niches = useNiches();
  const nicheName = (key: string) => niches.data?.niches.find((niche) => niche.key === key)?.name ?? "";
  const create = (
    <ButtonLink href={CREATE_PATH} leadingIcon={<IconPlus className="size-4" aria-hidden />}>
      {t("tunnel.newAssistant")}
    </ButtonLink>
  );

  return (
    <>
      <PageHeader title={t("businesses.title")} description={t("businesses.subtitle")} actions={businesses.length > 0 ? create : undefined} />

      {businesses.length === 0 ? (
        <Card>
          <EmptyState
            icon={<IconSparkles className="size-6" />}
            title={t("businesses.emptyTitle")}
            description={t("businesses.emptyDescription")}
            action={
              <ButtonLink href={CREATE_PATH} size="lg">
                {t("setup.start")}
              </ButtonLink>
            }
          />
        </Card>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {businesses.map((business) => (
            <li key={business.id}>
              <Link
                href={isBeingSetUp(business) ? setupPath(business.id) : businessPath(business.id)}
                className="group motion-lift flex h-full flex-col rounded-2xl border border-line bg-surface p-5 hover:border-line-strong hover:bg-surface-muted/40"
              >
                <div className="flex items-start justify-between gap-3">
                  <h2 className="min-w-0 text-base font-semibold break-words text-ink">{business.name}</h2>
                  <IconChevronRight className="mt-0.5 size-5 shrink-0 text-ink-subtle group-hover:text-accent rtl:-scale-x-100" aria-hidden />
                </div>
                <p className="mt-1 text-sm text-ink-muted">{nicheName(business.niche_key) || " "}</p>
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
    </>
  );
}
