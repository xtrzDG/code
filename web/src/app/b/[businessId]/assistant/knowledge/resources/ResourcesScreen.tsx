"use client";

import { useMemo, useState } from "react";

import { api } from "@/api/client";
import { useBookableOffers } from "@/api/offers";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { ConfirmDialog } from "@/components/ui";
import { IconCalendar, IconPlus } from "@/components/icons";
import { Alert, Button, Card, EmptyState, ErrorState, LoadingRegion, SkeletonRows, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { sortResources, type ResourceView } from "@/lib/resources";
import { formatLocalDate, splitExceptions, todayInTimeZone, type ScheduleExceptionView } from "@/lib/specialDays";

import { useNicheDetails } from "../_components/hooks";
import { ExceptionsCard } from "./_components/ExceptionsCard";
import { ResourceRow } from "./_components/ResourceRow";
import { ExceptionEditor } from "./ExceptionEditor";
import { ResourceEditor } from "./ResourceEditor";

/** Knowledge -> Resources and hours: what customers book, and holidays or special-hours days. */
export function ResourcesScreen() {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const niche = useNicheDetails();
  const today = useMemo(() => todayInTimeZone(new Date(), format.timeZone), [format.timeZone]);

  const resourcesKey = queryKeys.resources.list(business.id);
  const resources = useQuery(resourcesKey, () =>
    api.GET("/v1/businesses/{business_id}/resources", { params: { path: { business_id: business.id } } }),
  );
  const exceptions = useQuery(queryKeys.resources.exceptions(business.id), () =>
    api.GET("/v1/businesses/{business_id}/schedule-exceptions", { params: { path: { business_id: business.id } } }),
  );
  const offers = useBookableOffers(business.id);
  const profile = useQuery(queryKeys.profile.stored(business.id), () =>
    api.GET("/v1/businesses/{business_id}/profile", { params: { path: { business_id: business.id } } }),
  );

  const [resourceEditor, setResourceEditor] = useState<{ key: number; resource: ResourceView | null } | null>(null);
  const [exceptionEditor, setExceptionEditor] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<ScheduleExceptionView | null>(null);

  // The switch moves at once and goes back if the API refuses.
  const toggle = useMutation(
    (resource: ResourceView, isActive: boolean) =>
      api.PATCH("/v1/businesses/{business_id}/resources/{resource_id}", {
        params: { path: { business_id: business.id, resource_id: resource.id } },
        body: { is_active: isActive },
      }),
    {
      optimistic: (resource, isActive) =>
        queryCache.update<{ items?: ResourceView[] }>(resourcesKey, (data) => ({
          items: (data.items ?? []).map((item) => (item.id === resource.id ? { ...item, is_active: isActive } : item)),
        })),
      stale: [queryKeys.bookings.all(business.id), queryKeys.assistant.all(business.id)],
      invalidate: [queryKeys.assistant.pendingAll(business.id)],
    },
  );
  const removeException = useMutation(
    (exceptionId: string) =>
      api.DELETE("/v1/businesses/{business_id}/schedule-exceptions/{exception_id}", {
        params: { path: { business_id: business.id, exception_id: exceptionId } },
      }),
    { invalidate: [queryKeys.assistant.pendingAll(business.id)] },
  );

  const resourceList = sortResources(resources.data?.items ?? [], locale);
  const resourceName = (id: string | null | undefined) =>
    id ? (resourceList.find((resource) => resource.id === id)?.name ?? t("knowledge.exceptions.removedResource")) : null;
  const { upcoming, past } = splitExceptions(exceptions.data?.items ?? [], today);
  const nicheSummary = niche.data?.niche;

  const replaceResource = (saved: ResourceView) =>
    resources.setData((current) => {
      const list = current?.items ?? [];
      return {
        items: list.some((item) => item.id === saved.id) ? list.map((item) => (item.id === saved.id ? saved : item)) : [...list, saved],
      };
    });

  const setActive = async (resource: ResourceView, isActive: boolean) => {
    const result = await toggle.run(resource, isActive);
    if (result.ok) {
      replaceResource(result.data);
      toast.success(
        isActive
          ? t("knowledge.resources.switchedOn", { name: resource.name })
          : t("knowledge.resources.switchedOff", { name: resource.name }),
      );
    }
  };

  const confirmDelete = async () => {
    if (!deleting) {
      return;
    }
    const result = await removeException.run(deleting.id);
    if (result.ok) {
      const deletedId = deleting.id;
      exceptions.setData((current) => ({ items: (current?.items ?? []).filter((item) => item.id !== deletedId) }));
      toast.success(t("knowledge.exceptions.deleted", { date: formatLocalDate(deleting.date, locale) }));
      setDeleting(null);
    }
  };

  return (
    <div className="space-y-6">

      <Card
        padded={false}
        title={t("knowledge.resources.title")}
        description={
          nicheSummary ? t("knowledge.resources.description", { noun: nicheSummary.resource_noun }) : t("knowledge.resources.descriptionGeneric")
        }
        actions={
          <Button
            size="sm"
            leadingIcon={<IconPlus className="size-4" aria-hidden />}
            onClick={() => setResourceEditor((current) => ({ key: (current?.key ?? 0) + 1, resource: null }))}
          >
            {t("knowledge.resources.add")}
          </Button>
        }
      >
        {nicheSummary && !nicheSummary.takes_bookings ? (
          <Alert tone="info" className="mx-4 mt-4 sm:mx-6">
            {t("onboarding.booking.noBookings")}
          </Alert>
        ) : null}
        {resources.isLoading && !resources.data ? (
          <LoadingRegion label={t("common.loading")} className="p-4 sm:p-5">
            <SkeletonRows rows={3} />
          </LoadingRegion>
        ) : resources.error && !resources.data ? (
          <ErrorState error={resources.error} onRetry={resources.reload} />
        ) : resourceList.length === 0 ? (
          <EmptyState
            icon={<IconCalendar className="size-6" />}
            title={t("knowledge.resources.emptyTitle")}
            description={t("knowledge.resources.emptyDescription")}
          />
        ) : (
          <ul className="divide-y divide-line">
            {resourceList.map((resource) => (
              <ResourceRow
                key={resource.id}
                resource={resource}
                offers={offers.data ?? []}
                onToggle={(isActive) => void setActive(resource, isActive)}
                onEdit={() => setResourceEditor((current) => ({ key: (current?.key ?? 0) + 1, resource }))}
              />
            ))}
          </ul>
        )}
        <p className="border-t border-line px-4 py-3 text-sm text-ink-subtle sm:px-6">{t("knowledge.resources.noDeleteNote")}</p>
      </Card>

      <ExceptionsCard
        exceptions={exceptions}
        upcoming={upcoming}
        past={past}
        resourceName={resourceName}
        onAdd={() => setExceptionEditor((current) => (current ?? 0) + 1)}
        onDelete={setDeleting}
      />

      {resourceEditor ? (
        <ResourceEditor
          key={resourceEditor.key}
          resource={resourceEditor.resource}
          defaultKind={nicheSummary?.resource_kind ?? "table"}
          defaultBookingUnit={nicheSummary?.booking_unit ?? "time_slot"}
          businessHours={profile.data?.hours ?? []}
          onClose={() => setResourceEditor(null)}
          onSaved={(saved) => {
            replaceResource(saved);
                  setResourceEditor(null);
          }}
        />
      ) : null}

      {exceptionEditor !== null ? (
        <ExceptionEditor
          key={exceptionEditor}
          today={today}
          resources={resourceList.filter((resource) => resource.is_active)}
          onClose={() => setExceptionEditor(null)}
          onSaved={(saved) => {
            exceptions.setData((current) => ({ items: [...(current?.items ?? []), saved] }));
                  setExceptionEditor(null);
          }}
        />
      ) : null}

      <ConfirmDialog
        open={deleting !== null}
        title={t("knowledge.exceptions.deleteTitle")}
        description={deleting ? t("knowledge.exceptions.deleteDescription", { date: formatLocalDate(deleting.date, locale) }) : undefined}
        confirmLabel={t("common.delete")}
        isPending={removeException.isPending}
        onConfirm={() => void confirmDelete()}
        onClose={() => setDeleting(null)}
      />
    </div>
  );
}
