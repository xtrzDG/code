"use client";

/**
 * Customers → All customers: everyone who wrote, called or booked, newest
 * activity first, found by name, phone or ID, narrowed by a tag or to VIPs
 * or blocked ones. Staff see phones masked unless an owner allows them
 * (the switch under the list). Each row opens the customer's page.
 */

import { useEffect, useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconSearch, IconUsers } from "@/components/icons";
import { LoadMore, RefreshFailed } from "@/components/insights/common";
import { SegmentedControl } from "@/components/insights/SegmentedControl";
import { replaceUrlQuery } from "@/components/insights/urlQuery";
import { Button, EmptyState, ErrorState, Input, LoadingRegion, PageHeader, Select, SkeletonRows } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { CustomerRow } from "./_components/CustomerRow";
import { TeamAccessCard } from "./_components/TeamAccessCard";
import {
  CUSTOMER_LIST_FILTERS,
  customerFiltersQuery,
  customerListQuery,
  hasCustomerFilters,
  MAX_SEARCH_LENGTH,
  NO_CUSTOMER_FILTERS,
  type CustomerFilters,
  type CustomerListFilter,
} from "./_lib/customerFilters";
import { CUSTOMERS_PAGE_SIZE, type CustomerPage, type CustomerSummary } from "./_lib/customerModel";
import { StillIndexingNote } from "@/components/lists/StillIndexingNote";
import { useCustomerSettings } from "./_lib/useCustomerSettings";

const SEARCH_DELAY_MS = 300;

const FILTER_LABELS = {
  all: "customers.list.filters.all",
  vip: "customers.list.filters.vip",
  blocked: "customers.list.filters.blocked",
} as const;

export function CustomersScreen({ initialFilters }: { initialFilters: CustomerFilters }) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const settings = useCustomerSettings();
  const [typed, setTyped] = useState(initialFilters.search);
  const [filters, setFilters] = useState<CustomerFilters>(initialFilters);

  // The search follows the box after a pause; the URL follows the filters.
  useEffect(() => {
    const timer = window.setTimeout(() => setFilters((current) => ({ ...current, search: typed })), SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [typed]);
  const filtersQuery = customerFiltersQuery(filters);
  useEffect(() => replaceUrlQuery(filtersQuery), [filtersQuery]);

  const customers = useCursorPage<CustomerSummary, CustomerPage>(
    queryKeys.customers.list(business.id, filtersQuery),
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/contacts", {
        params: {
          path: { business_id: business.id },
          query: { ...customerListQuery(filters), limit: String(limit), ...(cursor ? { cursor } : {}) },
        },
      }),
    { pageSize: CUSTOMERS_PAGE_SIZE },
  );

  const knownTags = settings.data?.known_tags ?? [];
  const tagOptions = filters.tag && !knownTags.includes(filters.tag) ? [filters.tag, ...knownTags] : knownTags;
  const items = customers.items ?? [];
  const isEmpty = items.length === 0;
  const clear = () => {
    setTyped("");
    setFilters(NO_CUSTOMER_FILTERS);
  };

  return (
    <>
      <PageHeader title={t("navigation.pages.customersList")} description={t("navigation.descriptions.customersList")} />
      <div className="space-y-5">
        <div className="flex flex-wrap items-end gap-3">
          <div className="relative w-full max-w-md min-w-0 sm:w-auto sm:flex-1">
            <IconSearch className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-subtle" aria-hidden />
            <Input
              type="search"
              value={typed}
              maxLength={MAX_SEARCH_LENGTH}
              aria-label={t("customers.list.search")}
              placeholder={t("customers.list.searchPlaceholder")}
              title={t("settings.customers.searchHint")}
              className="pl-9"
              onChange={(event) => setTyped(event.target.value)}
            />
          </div>
          <SegmentedControl<CustomerListFilter>
            label={t("customers.list.filter")}
            value={filters.show}
            options={CUSTOMER_LIST_FILTERS.map((value) => ({ value, label: t(FILTER_LABELS[value]) }))}
            onChange={(show) => setFilters((current) => ({ ...current, show }))}
          />
          {tagOptions.length > 0 ? (
            <Select
              aria-label={t("customers.list.tag")}
              value={filters.tag ?? ""}
              className="w-full sm:w-48"
              onChange={(event) => setFilters((current) => ({ ...current, tag: event.target.value || null }))}
            >
              <option value="">{t("customers.list.anyTag")}</option>
              {tagOptions.map((tag) => (
                <option key={tag} value={tag}>
                  {tag}
                </option>
              ))}
            </Select>
          ) : null}
        </div>

        <StillIndexingNote isIndexing={customers.page?.is_indexing} />

        {customers.error && isEmpty ? (
          <ErrorState error={customers.error} onRetry={customers.reload} className="py-6" />
        ) : customers.isLoading && isEmpty ? (
          <LoadingRegion label={t("customers.loading")}>
            <SkeletonRows rows={6} avatar />
          </LoadingRegion>
        ) : isEmpty && !hasCustomerFilters(filters) ? (
          <EmptyState
            icon={<IconUsers className="size-6" />}
            title={t("customers.list.empty")}
            description={t("customers.list.emptyDescription")}
          />
        ) : isEmpty ? (
          <div className="flex flex-wrap items-center gap-3" role="status">
            <p className="text-sm text-ink-muted">{t("customers.list.noMatches")}</p>
            <Button variant="secondary" size="sm" onClick={clear}>
              {t("customers.list.clearFilters")}
            </Button>
          </div>
        ) : (
          <div className="space-y-3" aria-busy={customers.isPlaceholder || customers.isFetching}>
            {customers.error ? <RefreshFailed error={customers.error} onRetry={customers.reload} /> : null}
            <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
              {items.map((contact) => (
                <CustomerRow key={contact.id} contact={contact} />
              ))}
            </ul>
            <LoadMore
              hasMore={customers.hasMore}
              isLoading={customers.isLoadingMore}
              error={customers.moreError}
              onMore={customers.loadMore}
            />
          </div>
        )}

        {isOwner ? <TeamAccessCard settings={settings} /> : null}
      </div>
    </>
  );
}
