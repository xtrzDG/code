"use client";

import Link from "next/link";
import { useId } from "react";

import type { UserMembershipView } from "@/api/types";
import { groupMemberships, type MembershipGroup } from "@/app/brands/_lib/brands";
import { useI18n } from "@/i18n/client";
import { countryFlag } from "@/lib/countries";
import { brandPath, samePageIn } from "@/lib/navigation";

import { IconCheck, IconChevronRight } from "./icons";

/**
 * The switcher's businesses grouped by brand: each brand's locations under
 * its name (with a link to the brand's overview), then the businesses in
 * no brand. Without brands the list is one plain group, as before.
 */
export function BusinessSwitcherGroups({
  memberships,
  currentBusinessId,
  pathname,
  onNavigate,
}: {
  memberships: readonly UserMembershipView[];
  currentBusinessId: string;
  pathname: string;
  onNavigate: () => void;
}) {
  const groups = groupMemberships(memberships);
  const hasHeaders = groups.some((group) => group.brand !== null);
  return (
    <div className="max-h-80 overflow-y-auto py-1">
      {groups.map((group) => (
        <Group
          key={group.brand?.id ?? "others"}
          group={group}
          hasHeader={hasHeaders}
          currentBusinessId={currentBusinessId}
          pathname={pathname}
          onNavigate={onNavigate}
        />
      ))}
    </div>
  );
}

function Group({
  group,
  hasHeader,
  currentBusinessId,
  pathname,
  onNavigate,
}: {
  group: MembershipGroup;
  hasHeader: boolean;
  currentBusinessId: string;
  pathname: string;
  onNavigate: () => void;
}) {
  const { t } = useI18n();
  const headingId = useId();
  if (group.memberships.length === 0) {
    return null;
  }
  return (
    <div role="group" aria-labelledby={hasHeader ? headingId : undefined} className="py-1 [&+&]:border-t [&+&]:border-line">
      {hasHeader ? (
        <div className="flex items-center gap-2 px-3 pt-1.5 pb-1">
          <span id={headingId} className="min-w-0 flex-1 truncate text-xs font-semibold text-ink-subtle" data-user-content={group.brand ? true : undefined}>
            {group.brand ? group.brand.name : t("brands.switcher.others")}
          </span>
          {group.brand ? (
            <Link
              href={brandPath(group.brand.id)}
              onClick={onNavigate}
              className="inline-flex shrink-0 items-center gap-0.5 rounded text-xs font-medium text-accent hover:underline"
            >
              {t("brands.switcher.overview")}
              <IconChevronRight className="size-3.5 rtl:-scale-x-100" aria-hidden />
            </Link>
          ) : null}
        </div>
      ) : null}
      <ul>
        {group.memberships.map((membership) => {
          const isCurrent = membership.business_id === currentBusinessId;
          return (
            <li key={membership.business_id}>
              <Link
                href={samePageIn(membership.business_id, pathname)}
                aria-current={isCurrent ? "page" : undefined}
                onClick={onNavigate}
                className="flex min-h-10 items-center gap-2 px-3 py-2 text-sm text-ink hover:bg-surface-muted"
              >
                <span aria-hidden>{countryFlag(membership.country_code)}</span>
                <span className="min-w-0 flex-1 truncate" data-user-content>
                  {membership.business_name}
                </span>
                {isCurrent ? <IconCheck className="size-4 text-accent" aria-hidden /> : null}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
