"use client";

/**
 * Customers → Segments (owners): saved groups of customers by tag, last
 * visit, booking count and VIP mark, to see who is in each and download
 * them as CSV for a campaign. Blocked and erased customers never belong.
 */

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconPlus, IconUsers } from "@/components/icons";
import { AnimatedPresenceList } from "@/components/motion";
import { Alert, ConfirmDialog, EmptyState, ErrorState, PageHeader, SkeletonCardList, useToast } from "@/components/ui";
import { OwnerOnlyState } from "@/components/workspace/OwnerOnly";
import { useI18n } from "@/i18n/client";

import { SegmentCard } from "./_components/SegmentCard";
import { SegmentEditor } from "./_components/SegmentEditor";
import { MAX_SEGMENTS, type Segment } from "./_lib/segmentRules";
import { useSegmentExport } from "./_lib/useSegmentExport";

export function SegmentsScreen() {
  const { t } = useI18n();
  const toast = useToast();
  const { business, isOwner } = useBusiness();
  const exports = useSegmentExport();
  const [editing, setEditing] = useState<{ segment: Segment | null } | null>(null);
  const [deleting, setDeleting] = useState<Segment | null>(null);
  const segments = useQuery(
    queryKeys.customers.segments(business.id),
    () => api.GET("/v1/businesses/{business_id}/customer-segments", { params: { path: { business_id: business.id } } }),
    { enabled: isOwner },
  );
  const remove = useMutation(
    (segment: Segment) =>
      api.DELETE("/v1/businesses/{business_id}/customer-segments/{segment_id}", {
        params: { path: { business_id: business.id, segment_id: segment.id } },
      }),
    {
      errorToast: false,
      optimistic: (segment) => {
        const before = segments.data;
        segments.setData((current) =>
          current ? { ...current, items: (current.items ?? []).filter((item) => item.id !== segment.id) } : current,
        );
        return () => segments.setData(() => before);
      },
      invalidate: [queryKeys.customers.segments(business.id)],
    },
  );

  if (!isOwner || segments.error?.code === "access_denied") {
    return (
      <>
        <PageHeader title={t("navigation.pages.customersSegments")} />
        <OwnerOnlyState />
      </>
    );
  }

  const items = segments.data?.items ?? [];
  const isFull = items.length >= MAX_SEGMENTS;
  const openNew = () => setEditing({ segment: null });

  const onDelete = async () => {
    if (!deleting) {
      return;
    }
    const result = await remove.run(deleting);
    if (result.ok) {
      setDeleting(null);
      toast.success(t("segments.deleted"));
    }
  };

  return (
    <>
      <PageHeader
        title={t("navigation.pages.customersSegments")}
        description={t("navigation.descriptions.customersSegments")}
        primaryAction={
          isFull ? undefined : { label: t("segments.new"), icon: IconPlus, onClick: openNew, opensDialog: true }
        }
      />
      <div className="space-y-4">
        {isFull ? <Alert tone="info">{t("segments.limit")}</Alert> : null}
        {segments.error && !segments.data ? (
          <ErrorState error={segments.error} onRetry={segments.reload} />
        ) : !segments.data ? (
          <SkeletonCardList cards={2} />
        ) : items.length === 0 ? (
          <EmptyState
            icon={<IconUsers className="size-6" />}
            title={t("segments.empty")}
            description={t("segments.emptyDescription")}
          />
        ) : (
          <AnimatedPresenceList
            items={items}
            getKey={(segment) => segment.id}
            className="space-y-4"
            renderItem={(segment) => (
              <SegmentCard
                segment={segment}
                isExporting={exports.exporting === segment.id}
                onExport={() => void exports.download(segment)}
                onEdit={() => setEditing({ segment })}
                onDelete={() => setDeleting(segment)}
              />
            )}
          />
        )}
      </div>

      <SegmentEditor
        open={editing !== null}
        segment={editing?.segment ?? null}
        knownTags={segments.data?.known_tags ?? []}
        onClose={() => setEditing(null)}
      />
      <ConfirmDialog
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        onConfirm={onDelete}
        isPending={remove.isPending}
        error={remove.error}
        title={deleting ? t("segments.deleteTitle", { name: deleting.name }) : ""}
        confirmLabel={t("segments.delete")}
      >
        <p>{t("segments.deleteBody")}</p>
      </ConfirmDialog>
    </>
  );
}
