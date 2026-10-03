"use client";

import { useId, useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import type { OpeningInterval, ResourceKind, Weekday } from "@/api/types";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Button, Checkbox, Field, Fieldset, Input, Modal, Radio, Select, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import {
  BOOKING_UNITS,
  emptyResourceForm,
  RESOURCE_KINDS,
  resourceCreateBody,
  resourceFormFromView,
  resourcePatchBody,
  validateResourceForm,
  type BookingUnit,
  type ResourceCreateBody,
  type ResourceForm,
  type ResourceFormErrors,
  type ResourcePatchBody,
  type ResourceView,
} from "@/lib/resources";

import { HoursEditor, hoursToRows, rowsToHours, type DayRows } from "../../profile/_components/HoursEditor";

export const RESOURCE_KIND_LABELS: Record<ResourceKind, MessageKey> = {
  table: "onboarding.booking.resourceKinds.table",
  room: "onboarding.booking.resourceKinds.room",
  staff: "onboarding.booking.resourceKinds.staff",
  arena: "onboarding.booking.resourceKinds.arena",
  bay: "onboarding.booking.resourceKinds.bay",
  vehicle: "onboarding.booking.resourceKinds.vehicle",
  slot: "onboarding.booking.resourceKinds.slot",
};

export const BOOKING_UNIT_LABELS: Record<BookingUnit, MessageKey> = {
  time_slot: "knowledge.resources.bookingUnits.time_slot",
  night: "knowledge.resources.bookingUnits.night",
};

/** Add or edit a bookable resource, optionally with its own weekly hours. */
export function ResourceEditor({
  resource,
  defaultKind,
  defaultBookingUnit,
  businessHours,
  onClose,
  onSaved,
}: {
  /** Null to add a new resource. */
  resource: ResourceView | null;
  defaultKind: ResourceKind;
  defaultBookingUnit: BookingUnit;
  /** The business opening hours: the starting point for a resource's own hours. */
  businessHours: readonly OpeningInterval[];
  onClose: () => void;
  onSaved: (resource: ResourceView) => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const formId = useId();

  const [form, setForm] = useState<ResourceForm>(() =>
    resource ? resourceFormFromView(resource) : emptyResourceForm(defaultKind, defaultBookingUnit),
  );
  const [days, setDays] = useState<DayRows[]>(() =>
    hoursToRows((resource?.schedule ?? []).length > 0 ? (resource?.schedule ?? []) : businessHours),
  );
  const [errors, setErrors] = useState<ResourceFormErrors>({});
  const [hoursErrors, setHoursErrors] = useState<Partial<Record<Weekday, MessageKey>>>({});
  const [hoursMissing, setHoursMissing] = useState(false);

  // What the assistant knows changed: the changes customers do not get yet are read again.
  const settled = { invalidate: [queryKeys.assistant.pendingAll(business.id)] };
  const create = useMutation(
    (body: ResourceCreateBody) =>
      api.POST("/v1/businesses/{business_id}/resources", { params: { path: { business_id: business.id } }, body }),
    settled,
  );
  const update = useMutation(
    (resourceId: string, body: ResourcePatchBody) =>
      api.PATCH("/v1/businesses/{business_id}/resources/{resource_id}", {
        params: { path: { business_id: business.id, resource_id: resourceId } },
        body,
      }),
    settled,
  );

  const change = (patch: Partial<ResourceForm>) => {
    setForm((current) => ({ ...current, ...patch }));
    setErrors((current) => {
      const next = { ...current };
      for (const key of Object.keys(patch)) {
        delete next[key as keyof ResourceFormErrors];
      }
      return next;
    });
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const found = validateResourceForm(form);
    setErrors(found);
    let schedule: OpeningInterval[] = [];
    let hoursValid = true;
    if (form.hasOwnSchedule) {
      const hours = rowsToHours(days);
      setHoursErrors(hours.ok ? {} : hours.errors);
      setHoursMissing(hours.ok && hours.hours.length === 0);
      hoursValid = hours.ok && hours.hours.length > 0;
      schedule = hours.ok ? hours.hours : [];
    }
    if (Object.keys(found).length > 0 || !hoursValid) {
      return;
    }
    if (!resource) {
      const result = await create.run(resourceCreateBody(form, schedule));
      if (result.ok) {
        toast.success(t("knowledge.resources.added", { name: result.data.name }));
        onSaved(result.data);
      }
      return;
    }
    const patch = resourcePatchBody(form, resource, schedule);
    if (Object.keys(patch).length === 0) {
      onClose();
      return;
    }
    const result = await update.run(resource.id, patch);
    if (result.ok) {
      toast.success(t("common.saved"));
      onSaved(result.data);
    }
  };

  const isPending = create.isPending || update.isPending;

  return (
    <Modal
      open
      onClose={() => {
        if (!isPending) {
          onClose();
        }
      }}
      size="xl"
      title={resource ? t("knowledge.resources.editTitle") : t("knowledge.resources.addTitle")}
      description={t("knowledge.resources.editorDescription")}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isPending}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" form={formId} isLoading={isPending} loadingText={t("common.saving")}>
            {resource ? t("common.save") : t("knowledge.resources.add")}
          </Button>
        </>
      }
    >
      <form id={formId} onSubmit={(event) => void submit(event)} noValidate className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-6">
          <Field label={t("knowledge.resources.name")} error={errors.name && t(errors.name)} required className="sm:col-span-4">
            {(control) => (
              <Input
                {...control}
                dir="auto"
                autoFocus
                maxLength={200}
                placeholder={t("onboarding.resources.namePlaceholder")}
                value={form.name}
                onChange={(event) => change({ name: event.target.value })}
              />
            )}
          </Field>
          <Field label={t("knowledge.resources.kind")} className="sm:col-span-2">
            {(control) => (
              <Select {...control} value={form.kind} onChange={(event) => change({ kind: event.target.value as ResourceKind })}>
                {RESOURCE_KINDS.map((kind) => (
                  <option key={kind} value={kind}>
                    {t(RESOURCE_KIND_LABELS[kind])}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field
            label={t("knowledge.resources.capacity")}
            hint={t("knowledge.resources.capacityHint")}
            error={errors.capacity && t(errors.capacity)}
            required
            className="sm:col-span-2"
          >
            {(control) => (
              <Input {...control} inputMode="numeric" value={form.capacity} onChange={(event) => change({ capacity: event.target.value })} />
            )}
          </Field>
          <Field
            label={t("knowledge.resources.units")}
            hint={t("knowledge.resources.unitsHint")}
            error={errors.units && t(errors.units)}
            required
            className="sm:col-span-2"
          >
            {(control) => (
              <Input {...control} inputMode="numeric" value={form.units} onChange={(event) => change({ units: event.target.value })} />
            )}
          </Field>
          <Field
            label={t("knowledge.resources.slotMinutes")}
            hint={t("knowledge.resources.slotMinutesHint")}
            optionalLabel={t("common.optional")}
            error={errors.slotMinutes && t(errors.slotMinutes)}
            className="sm:col-span-2"
          >
            {(control) => (
              <Input {...control} inputMode="numeric" value={form.slotMinutes} onChange={(event) => change({ slotMinutes: event.target.value })} />
            )}
          </Field>
          <Field label={t("knowledge.resources.bookingUnit")} className="sm:col-span-3">
            {(control) => (
              <Select {...control} value={form.bookingUnit} onChange={(event) => change({ bookingUnit: event.target.value as BookingUnit })}>
                {BOOKING_UNITS.map((unit) => (
                  <option key={unit} value={unit}>
                    {t(BOOKING_UNIT_LABELS[unit])}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <div className="sm:col-span-3 sm:pt-7">
            <Checkbox
              id={`${formId}-active`}
              label={t("knowledge.resources.active")}
              description={t("knowledge.resources.activeHint")}
              checked={form.isActive}
              onChange={(event) => change({ isActive: event.target.checked })}
            />
          </div>
        </div>

        <Fieldset legend={t("knowledge.resources.hours")} hint={t("knowledge.resources.hoursHint", { timezone: format.timeZone })}>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <Radio
              id={`${formId}-hours-business`}
              name={`${formId}-hours`}
              label={t("knowledge.resources.hoursBusiness")}
              checked={!form.hasOwnSchedule}
              onChange={() => change({ hasOwnSchedule: false })}
            />
            <Radio
              id={`${formId}-hours-own`}
              name={`${formId}-hours`}
              label={t("knowledge.resources.hoursOwn")}
              checked={form.hasOwnSchedule}
              onChange={() => change({ hasOwnSchedule: true })}
            />
          </div>
          {form.hasOwnSchedule ? (
            <HoursEditor
              days={days}
              errors={hoursErrors}
              onChange={(next) => {
                setDays(next);
                setHoursErrors({});
                setHoursMissing(false);
              }}
            />
          ) : null}
          {form.hasOwnSchedule && hoursMissing ? (
            <p className="text-sm text-danger" role="alert">
              {t("knowledge.resources.errors.hoursRequired")}
            </p>
          ) : null}
        </Fieldset>
      </form>
    </Modal>
  );
}
