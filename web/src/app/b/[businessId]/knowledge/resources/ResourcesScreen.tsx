"use client";

import { useMemo, useState } from "react";

import { api } from "@/api/client";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { ConfirmDialog } from "@/components/content/ConfirmDialog";
import { IconCalendar, IconPlus } from "@/components/icons";
import { Alert, Button, Card, EmptyState, ErrorState, LoadingBlock, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import {
  formatLocalDate,
  sortResources,
  splitExceptions,
  todayInTimeZone,
  type ResourceView,
  type ScheduleExceptionView,
} from "@/lib/resources";

import { useNicheDetails } from "../_components/hooks";
import { ReassemblyNotice } from "../_components/ReassemblyNotice";
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

  const resources = useApiQuery(
    () => api.GET("/v1/businesses/{business_id}/resources", { params: { path: { business_id: business.id } } }),
    [business.id],
  );
  const exceptions = useApiQuery(
    () => api.GET("/v1/businesses/{business_id}/schedule-exceptions", { params: { path: { business_id: business.id } } }),
    [business.id],
  );
  const profile = useApiQuery(
    () => api.GET("/v1/businesses/{business_id}/profile", { params: { path: { business_id: business.id } } }),
    [business.id],
  );

  const [resourceEditor, setResourceEditor] = useState<{ key: number; resource: ResourceView | null } | null>(null);
  const [exceptionEditor, setExceptionEditor] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<ScheduleExceptionView | null>(null);
  const [toggling, setToggling] = useState<ReadonlySet<string>>(new Set());
  const [hasChanges, setHasChanges] = useState(false);

  const toggle = useApiMutation((resourceId: string, isActive: boolean) =>
    api.PATCH("/v1/businesses/{business_id}/resources/{resource_id}", {
      params: { path: { business_id: business.id, resource_id: resourceId } },
      body: { is_active: isActive },
    }),
  );
  const removeException = useApiMutation((exceptionId: string) =>
    api.DELETE("/v1/businesses/{business_id}/schedule-exceptions/{exception_id}", {
      params: { path: { business_id: business.id, exception_id: exceptionId } },
    }),
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
    setToggling((current) => new Set(current).add(resource.id));
    const result = await toggle.run(resource.id, isActive);
    setToggling((current) => {
      const next = new Set(current);
      next.delete(resource.id);
      return next;
    });
    if (result.ok) {
      replaceResource(result.data);
      setHasChanges(true);
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
      setHasChanges(true);
      setDeleting(null);
    }
  };

  return (
    <div className="space-y-6">
      {hasChanges ? <ReassemblyNotice /> : null}

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
          <LoadingBlock label={t("common.loading")} />
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
                isToggling={toggling.has(resource.id)}
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
            setHasChanges(true);
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
            setHasChanges(true);
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
