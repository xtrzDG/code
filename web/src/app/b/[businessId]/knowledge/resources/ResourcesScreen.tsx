"use client";

import { useMemo, useState } from "react";

import { api } from "@/api/client";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { ConfirmDialog } from "@/components/content/ConfirmDialog";
import { IconPencil } from "@/components/content/icons";
import { Switch } from "@/components/content/Switch";
import { IconCalendar, IconClock, IconPlus, IconTrash } from "@/components/icons";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingBlock,
  Spinner,
  useToast,
} from "@/components/ui";
import { useI18n } from "@/i18n/client";
import {
  formatLocalDate,
  intervalsLabel,
  sortResources,
  splitExceptions,
  todayInTimeZone,
  type ResourceView,
  type ScheduleExceptionView,
} from "@/lib/resources";

import { useNicheDetails } from "../_components/hooks";
import { ReassemblyNotice } from "../_components/ReassemblyNotice";
import { ExceptionEditor } from "./ExceptionEditor";
import { BOOKING_UNIT_LABELS, RESOURCE_KIND_LABELS, ResourceEditor } from "./ResourceEditor";

/** Knowledge -> Resources and hours: what customers book, and holidays or special-hours days. */
export function ResourcesScreen() {
  const { t, tp, locale } = useI18n();
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
  const [showPast, setShowPast] = useState(false);
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

  const renderException = (exception: ScheduleExceptionView, isPast: boolean) => {
    const appliesTo = resourceName(exception.resource_id);
    return (
      <li key={exception.id} className="flex flex-col gap-2 px-4 py-4 sm:flex-row sm:items-start sm:gap-6 sm:px-6">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className={isPast ? "font-medium text-ink-muted" : "font-medium text-ink"}>{formatLocalDate(exception.date, locale)}</p>
            {exception.is_closed_all_day ? (
              <Badge tone="danger">{t("knowledge.exceptions.closed")}</Badge>
            ) : (
              <Badge tone="info" icon={<IconClock className="size-3.5" aria-hidden />}>
                {intervalsLabel(exception.special_hours ?? [])}
              </Badge>
            )}
          </div>
          <p className="text-sm text-ink-subtle">{appliesTo ?? t("knowledge.exceptions.wholeBusiness")}</p>
          {exception.note ? (
            <p className="text-sm break-words text-ink-muted" dir="auto">
              {exception.note}
            </p>
          ) : null}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="self-start hover:text-danger"
          leadingIcon={<IconTrash className="size-4" aria-hidden />}
          aria-label={`${t("common.delete")}: ${formatLocalDate(exception.date, locale)}`}
          onClick={() => setDeleting(exception)}
        >
          {t("common.delete")}
        </Button>
      </li>
    );
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
            {resourceList.map((resource) => {
              const details = [
                t(RESOURCE_KIND_LABELS[resource.kind]),
                tp("knowledge.resources.capacityValue", resource.capacity),
                resource.unit_count > 1 ? t("knowledge.resources.unitsValue", { count: resource.unit_count }) : null,
                resource.slot_minutes ? t("knowledge.resources.slotValue", { count: resource.slot_minutes }) : null,
                resource.booking_unit === "night" ? t(BOOKING_UNIT_LABELS.night) : null,
              ].filter((part): part is string => part !== null);
              const ownHours = resource.schedule ?? [];
              return (
                <li key={resource.id} className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start sm:gap-6 sm:px-6">
                  <div className="min-w-0 flex-1 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className={resource.is_active ? "font-medium text-ink" : "font-medium text-ink-muted"} dir="auto">
                        {resource.name}
                      </p>
                      {!resource.is_active ? <Badge>{t("knowledge.resources.inactive")}</Badge> : null}
                    </div>
                    <p className="text-sm text-ink-subtle">{details.join(" · ")}</p>
                    <p className="text-sm text-ink-subtle">
                      {ownHours.length > 0 ? t("knowledge.resources.ownHoursSet") : t("knowledge.resources.followsBusiness")}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <span className="mr-2 flex items-center gap-2">
                      {toggling.has(resource.id) ? <Spinner size="sm" /> : null}
                      <Switch
                        checked={resource.is_active}
                        disabled={toggling.has(resource.id)}
                        label={t("knowledge.resources.toggle", { name: resource.name })}
                        onChange={(isActive) => void setActive(resource, isActive)}
                      />
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      leadingIcon={<IconPencil className="size-4" aria-hidden />}
                      aria-label={`${t("common.edit")}: ${resource.name}`}
                      onClick={() => setResourceEditor((current) => ({ key: (current?.key ?? 0) + 1, resource }))}
                    >
                      {t("common.edit")}
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        <p className="border-t border-line px-4 py-3 text-sm text-ink-subtle sm:px-6">{t("knowledge.resources.noDeleteNote")}</p>
      </Card>

      <Card
        padded={false}
        title={t("knowledge.exceptions.title")}
        description={t("knowledge.exceptions.description", { timezone: format.timeZone })}
        actions={
          <Button
            size="sm"
            leadingIcon={<IconPlus className="size-4" aria-hidden />}
            onClick={() => setExceptionEditor((current) => (current ?? 0) + 1)}
          >
            {t("knowledge.exceptions.add")}
          </Button>
        }
      >
        {exceptions.isLoading && !exceptions.data ? (
          <LoadingBlock label={t("common.loading")} />
        ) : exceptions.error && !exceptions.data ? (
          <ErrorState error={exceptions.error} onRetry={exceptions.reload} />
        ) : upcoming.length === 0 && past.length === 0 ? (
          <EmptyState
            icon={<IconCalendar className="size-6" />}
            title={t("knowledge.exceptions.emptyTitle")}
            description={t("knowledge.exceptions.emptyDescription")}
          />
        ) : (
          <>
            {upcoming.length === 0 ? (
              <p className="px-4 py-6 text-sm text-ink-muted sm:px-6">{t("knowledge.exceptions.noUpcoming")}</p>
            ) : (
              <ul className="divide-y divide-line">{upcoming.map((exception) => renderException(exception, false))}</ul>
            )}
            {past.length > 0 ? (
              <div className="border-t border-line">
                <div className="px-4 py-3 sm:px-6">
                  <Button variant="ghost" size="sm" aria-expanded={showPast} onClick={() => setShowPast((value) => !value)}>
                    {showPast ? t("knowledge.exceptions.hidePast") : t("knowledge.exceptions.showPast", { count: past.length })}
                  </Button>
                </div>
                {showPast ? <ul className="divide-y divide-line border-t border-line">{past.map((exception) => renderException(exception, true))}</ul> : null}
              </div>
            ) : null}
          </>
        )}
      </Card>

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
