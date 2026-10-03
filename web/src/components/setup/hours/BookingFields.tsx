"use client";

/**
 * "How do bookings work?" as a few plain choices: how long a visit takes
 * (not for nights), the most people in one booking, how much notice, the
 * cancellation rule, and the first bookable place when there is none yet.
 */

import { Field, Input, Select, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { noticeChoices, slotChoices, type BookingForm, type BookingProblem, type ResourceForm } from "@/lib/tunnel/bookings";

function useDurations() {
  const { t, tp } = useI18n();
  const length = (minutes: number) => {
    if (minutes % 60 === 0) {
      return tp("tunnelOffer.hours.hoursCount", minutes / 60);
    }
    return tp("tunnelOffer.hours.minutes", minutes);
  };
  const notice = (minutes: number) => {
    if (minutes === 0) {
      return t("tunnelOffer.hours.noticeNone");
    }
    if (minutes % 1440 === 0) {
      return tp("tunnelOffer.hours.noticeDays", minutes / 1440);
    }
    if (minutes % 60 === 0) {
      return tp("tunnelOffer.hours.noticeHours", minutes / 60);
    }
    return tp("tunnelOffer.hours.noticeMinutes", minutes);
  };
  return { length, notice };
}

export function BookingFields({
  form,
  onChange,
  bySlots,
  resource,
  onResource,
  problem,
}: {
  form: BookingForm;
  onChange: (form: BookingForm) => void;
  /** Visits by length (false for nights: hotels, rentals). */
  bySlots: boolean;
  /** The first bookable place to create; null when the business has one. */
  resource: ResourceForm | null;
  onResource: (form: ResourceForm) => void;
  problem: BookingProblem | null;
}) {
  const { t } = useI18n();
  const durations = useDurations();
  const errorFor = (which: BookingProblem) => (problem === which ? t(`tunnelOffer.hours.errors.${which}`) : undefined);

  return (
    <div className="space-y-6">
      <div className="grid gap-5 sm:grid-cols-3">
        {bySlots ? (
          <Field label={t("tunnelOffer.hours.slot")}>
            {(control) => (
              <Select {...control} value={String(form.slotMinutes)} onChange={(event) => onChange({ ...form, slotMinutes: Number(event.target.value) })}>
                {slotChoices(form.slotMinutes).map((minutes) => (
                  <option key={minutes} value={minutes}>
                    {durations.length(minutes)}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        ) : null}
        <Field label={t("tunnelOffer.hours.partySize")} error={errorFor("partySize")}>
          {(control) => (
            <Input
              {...control}
              inputMode="numeric"
              value={form.maxPartySize}
              onChange={(event) => onChange({ ...form, maxPartySize: event.target.value })}
            />
          )}
        </Field>
        <Field label={t("tunnelOffer.hours.notice")}>
          {(control) => (
            <Select
              {...control}
              value={String(form.minNoticeMinutes)}
              onChange={(event) => onChange({ ...form, minNoticeMinutes: Number(event.target.value) })}
            >
              {noticeChoices(form.minNoticeMinutes).map((minutes) => (
                <option key={minutes} value={minutes}>
                  {durations.notice(minutes)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>

      <Field label={t("tunnelOffer.hours.cancellation")} hint={t("tunnelOffer.hours.cancellationHint")} optionalLabel={t("common.optional")}>
        {(control) => (
          <Textarea
            {...control}
            rows={2}
            maxLength={1000}
            value={form.cancellationPolicy}
            onChange={(event) => onChange({ ...form, cancellationPolicy: event.target.value })}
          />
        )}
      </Field>

      {resource ? (
        <fieldset className="space-y-3 rounded-xl border border-line bg-surface-muted/40 p-4">
          <legend className="px-1 text-sm font-semibold text-ink">{t("tunnelOffer.hours.resourceTitle")}</legend>
          <p className="text-sm text-ink-muted">{t("tunnelOffer.hours.resourceHint")}</p>
          <div className="grid gap-4 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)]">
            <Field label={t("tunnelOffer.hours.resourceName")} error={errorFor("resourceName")}>
              {(control) => <Input {...control} value={resource.name} maxLength={120} onChange={(event) => onResource({ ...resource, name: event.target.value })} />}
            </Field>
            <Field label={t("tunnelOffer.hours.resourceCount")} error={errorFor("unitCount")}>
              {(control) => (
                <Input {...control} inputMode="numeric" value={resource.unitCount} onChange={(event) => onResource({ ...resource, unitCount: event.target.value })} />
              )}
            </Field>
            <Field label={t("tunnelOffer.hours.resourceCapacity")} error={errorFor("capacity")}>
              {(control) => (
                <Input {...control} inputMode="numeric" value={resource.capacity} onChange={(event) => onResource({ ...resource, capacity: event.target.value })} />
              )}
            </Field>
          </div>
        </fieldset>
      ) : null}
    </div>
  );
}
