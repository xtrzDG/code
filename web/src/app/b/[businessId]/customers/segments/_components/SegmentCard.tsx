"use client";

/**
 * One saved segment: its name and rules as a sentence, its customers
 * (shown on demand, a page at a time), the CSV download, edit and delete.
 */

import { useId, useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconChevronDown, IconDownload, IconPencil, IconTrash } from "@/components/icons";
import { LoadMore } from "@/components/insights/common";
import { Button, Card, ErrorState, LoadingRegion, SkeletonRows } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { CustomerRow } from "../../_components/CustomerRow";
import { CUSTOMERS_PAGE_SIZE, type CustomerPage, type CustomerSummary } from "../../_lib/customerModel";
import { summaryParts, type Segment } from "../_lib/segmentRules";

function SegmentMembers({ segment }: { segment: Segment }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const members = useCursorPage<CustomerSummary, CustomerPage>(
    queryKeys.customers.members(business.id, segment.id),
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/customer-segments/{segment_id}/members", {
        params: {
          path: { business_id: business.id, segment_id: segment.id },
          query: { limit: String(limit), ...(cursor ? { cursor } : {}) },
        },
      }),
    { pageSize: CUSTOMERS_PAGE_SIZE },
  );
  const items = members.items ?? [];
  if (members.error && items.length === 0) {
    return <ErrorState error={members.error} onRetry={members.reload} className="py-4" />;
  }
  if (members.isLoading && items.length === 0) {
    return (
      <LoadingRegion label={t("segments.loading")}>
        <SkeletonRows rows={3} avatar />
      </LoadingRegion>
    );
  }
  if (items.length === 0) {
    return <p className="text-sm text-ink-muted">{t("segments.noMembers")}</p>;
  }
  return (
    <div className="space-y-2">
      <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line">
        {items.map((contact) => (
          <CustomerRow key={contact.id} contact={contact} />
        ))}
      </ul>
      <LoadMore hasMore={members.hasMore} isLoading={members.isLoadingMore} error={members.moreError} onMore={members.loadMore} />
    </div>
  );
}

export function SegmentCard({
  segment,
  isExporting,
  onExport,
  onEdit,
  onDelete,
}: {
  segment: Segment;
  isExporting: boolean;
  onExport: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t, tp } = useI18n();
  const membersId = useId();
  const [isOpen, setOpen] = useState(false);
  const summary = summaryParts(segment.rules)
    .map((part) => ("plural" in part ? tp(part.plural, part.count) : t(part.key, part.values)))
    .join(" · ");

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1 basis-60">
          <h3 dir="auto" className="text-base font-semibold break-words text-ink">
            {segment.name}
          </h3>
          <p dir="auto" className="mt-1 text-sm text-ink-muted">
            {summary}
          </p>
        </div>
        <div className="flex flex-wrap gap-1">
          <Button
            variant="secondary"
            size="sm"
            leadingIcon={<IconDownload className="size-4" aria-hidden />}
            isLoading={isExporting}
            title={t("segments.exportHint")}
            onClick={onExport}
          >
            {t("segments.export")}
          </Button>
          <Button variant="ghost" size="sm" leadingIcon={<IconPencil className="size-4" aria-hidden />} onClick={onEdit}>
            {t("segments.edit")}
          </Button>
          <Button variant="danger-ghost" size="sm" leadingIcon={<IconTrash className="size-4" aria-hidden />} onClick={onDelete}>
            {t("segments.delete")}
          </Button>
        </div>
      </div>
      <button
        type="button"
        aria-expanded={isOpen}
        aria-controls={membersId}
        onClick={() => setOpen((current) => !current)}
        className="mt-3 inline-flex cursor-pointer items-center gap-1 text-sm font-medium text-accent hover:underline"
      >
        {t("segments.members")}
        <IconChevronDown className={cn("size-4 transition-transform", isOpen && "rotate-180")} aria-hidden />
      </button>
      <div id={membersId} className="mt-3" hidden={!isOpen}>
        {isOpen ? <SegmentMembers segment={segment} /> : null}
      </div>
    </Card>
  );
}
