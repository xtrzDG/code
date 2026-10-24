"use client";

/**
 * "Regular customer · 4 visits" under a conversation's name, linking to
 * the customer's page. Nothing while it loads or when the API has no
 * answer (an erased customer, a test conversation): the header stays as
 * it was.
 */

import Link from "next/link";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { IconStar } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { customerPath } from "@/lib/navigation";

import { standingLine } from "./standing";

const STANDING_STALE_MS = 60_000;

export function CustomerStandingLink({
  businessId,
  contactId,
  className,
}: {
  businessId: string;
  contactId: string | null;
  className?: string;
}) {
  const i18n = useI18n();
  const standing = useQuery(
    queryKeys.customers.standing(businessId, contactId ?? ""),
    () =>
      api.GET("/v1/businesses/{business_id}/contacts/{contact_id}/standing", {
        params: { path: { business_id: businessId, contact_id: contactId ?? "" } },
      }),
    { enabled: Boolean(contactId), staleMs: STANDING_STALE_MS },
  );
  const view = standing.data;
  if (!contactId || !view || view.is_erased) {
    return null;
  }
  const line = standingLine(i18n, view.standing, view.visit_count);
  return (
    <Link
      href={customerPath(businessId, contactId)}
      aria-label={i18n.t("customers.standing.open", { line })}
      className={cn(
        "inline-flex max-w-full items-center gap-1 truncate text-xs font-medium text-accent hover:underline",
        className,
      )}
    >
      {view.is_vip ? <IconStar className="size-3 shrink-0" aria-hidden /> : null}
      <span className="truncate">{line}</span>
    </Link>
  );
}
