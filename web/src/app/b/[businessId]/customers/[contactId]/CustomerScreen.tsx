"use client";

/**
 * One customer's page: who they are and their standing, their history
 * across channels (conversations, bookings, requests, calls), the team's
 * card (tags, VIP), and for owners blocking and data requests (export,
 * erase). Each opening is audited by the API as a view of personal data;
 * staff see the phone masked unless an owner allows it.
 */

import Link from "next/link";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconArrowLeft, IconUsers } from "@/components/icons";
import { EmptyState, ErrorState, LoadingRegion, PageHeader, SkeletonCard, UserContent } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { customerNaming } from "../_lib/customerModel";
import { useCustomerSettings } from "../_lib/useCustomerSettings";
import { BlockCard } from "./_components/BlockCard";
import { CustomerCardEditor } from "./_components/CustomerCardEditor";
import { CustomerDataCard } from "./_components/CustomerDataCard";
import { CustomerSummaryCard } from "./_components/CustomerSummaryCard";
import { CustomerTimeline } from "./_components/CustomerTimeline";

export function CustomerScreen({ contactId }: { contactId: string }) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const settings = useCustomerSettings();
  const detail = useQuery(
    queryKeys.customers.detail(business.id, contactId),
    () =>
      api.GET("/v1/businesses/{business_id}/contacts/{contact_id}", {
        params: { path: { business_id: business.id, contact_id: contactId } },
      }),
    // Every load is an audited view: no reload on each visit within a minute.
    { staleMs: 60_000 },
  );

  const back = (
    <Link
      href={businessPath(business.id, "customers")}
      className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-muted hover:text-ink"
    >
      <IconArrowLeft className="size-4 rtl:-scale-x-100" aria-hidden />
      {t("customers.detail.back")}
    </Link>
  );

  const data = detail.data;
  if (!data) {
    return (
      <>
        <PageHeader title={t("navigation.pages.customersList")} eyebrow={back} />
        {detail.error?.code === "not_found" ? (
          <EmptyState icon={<IconUsers className="size-6" />} title={t("customers.detail.notFound")} />
        ) : detail.error ? (
          <ErrorState error={detail.error} onRetry={detail.reload} />
        ) : (
          <LoadingRegion label={t("customers.loading")}>
            <SkeletonCard header={false} lines={2} />
          </LoadingRegion>
        )}
      </>
    );
  }

  const naming = customerNaming(data.contact, { unnamed: t("palette.unnamed"), erased: t("settings.customers.erasedName") });

  return (
    <>
      <PageHeader title={naming.isOwn ? <UserContent>{naming.name}</UserContent> : naming.name} eyebrow={back} />
      <div className="space-y-6">
        <CustomerSummaryCard detail={data} naming={naming} />
        <div className="grid items-start gap-6 lg:grid-cols-3">
          <div className="min-w-0 lg:col-span-2">
            <CustomerTimeline entries={data.timeline ?? []} />
          </div>
          <div className="min-w-0 space-y-6">
            <CustomerCardEditor detail={detail} knownTags={settings.data?.known_tags ?? []} />
            {isOwner ? <BlockCard detail={detail} naming={naming} /> : null}
            {isOwner ? <CustomerDataCard detail={detail} naming={naming} /> : null}
          </div>
        </div>
      </div>
    </>
  );
}
