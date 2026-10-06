"use client";

/**
 * A time of day in the cabinet's language: segments for the hours and
 * minutes (and AM/PM where the locale's clock has them: English), so a
 * Russian or Georgian cabinet reads "08:00" whatever the browser's own
 * language is. The value is "HH:MM" on a 24-hour clock, "" while empty or
 * half typed.
 *
 *     <Field label={t("…opens")}>
 *       {(control) => <TimeField {...control} value={opens} onChange={setOpens} />}
 *     </Field>
 *
 * Inside a Field the field is labelled by the Field's label and the hours
 * take its id (a click on the label focuses them); without one, pass
 * `aria-label`. Each segment is a spinbutton: arrows step the hours by one
 * and the minutes by `step` (15 or 30); typing "0830" fills both; the
 * spoken value is the whole time in the cabinet's language.
 */

import { useId, type FocusEvent } from "react";

import { IconClock } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { mergeClassOverrides } from "@/lib/classMerge";
import { cn } from "@/lib/cn";
import { dayPeriods, hourCycle } from "@/lib/intl/localeCalendar";
import { minutesOf, timeText } from "@/lib/timeInput";
import { hourText, periodOfDraft, type TimeDraft, type TimeSegment } from "@/lib/timeSegments";

import { fieldLabelId } from "./Field";
import { useTimeField } from "./useTimeField";

export interface TimeFieldProps {
  value: string;
  onChange: (value: string) => void;
  /** From a Field: the hours take it, and the field is labelled by `#{id}-label`. */
  id?: string;
  /** The label's id when it is not the Field's own (a date and time field shares one label). */
  labelId?: string;
  "aria-label"?: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean | "true" | "false";
  required?: boolean;
  disabled?: boolean;
  /** Minutes an arrow press moves the minutes by. */
  step?: number;
  /** Where the arrows start in an empty field ("09:00"). */
  defaultTime?: string;
  className?: string;
  /** The focus left the whole field. */
  onBlur?: () => void;
}

const SEGMENT_NAMES = {
  hour: "formFields.time.hours",
  minute: "formFields.time.minutes",
  period: "formFields.time.dayPeriod",
} as const satisfies Record<TimeSegment, string>;

function segmentRange(segment: TimeSegment, isTwelveHour: boolean): { min: number; max: number } {
  if (segment === "hour") {
    return isTwelveHour ? { min: 1, max: 12 } : { min: 0, max: 23 };
  }
  return segment === "minute" ? { min: 0, max: 59 } : { min: 0, max: 1 };
}

function segmentNumber(draft: TimeDraft, segment: TimeSegment, isTwelveHour: boolean): number | undefined {
  if (segment === "hour") {
    return draft.hour === null ? undefined : isTwelveHour ? draft.hour % 12 || 12 : draft.hour;
  }
  if (segment === "minute") {
    return draft.minute ?? undefined;
  }
  const period = periodOfDraft(draft);
  return period === null ? undefined : period === "am" ? 0 : 1;
}

export function TimeField({
  value,
  onChange,
  id,
  labelId,
  "aria-label": ariaLabel,
  "aria-describedby": describedBy,
  "aria-invalid": invalid,
  required,
  disabled = false,
  step = 15,
  defaultTime,
  className,
  onBlur,
}: TimeFieldProps) {
  const { t, locale } = useI18n();
  const ownId = useId();
  const groupId = `${ownId}-group`;
  const isTwelveHour = hourCycle(locale) === "h12";
  const periods = dayPeriods(locale);
  const field = useTimeField({ value, onChange, locale, step, defaultTime });
  const { draft, pending } = field;
  const label = labelId ?? (id ? fieldLabelId(id) : groupId);
  const minutes = minutesOf(value);
  const spoken = minutes === null ? t("formFields.time.empty") : timeText(minutes, locale);

  const shownText = (segment: TimeSegment): string => {
    if (pending?.segment === segment) {
      return pending.buffer.padStart(2, "0");
    }
    if (segment === "hour") {
      return draft.hour === null ? "" : hourText(draft.hour, isTwelveHour ? "h12" : "h23");
    }
    if (segment === "minute") {
      return draft.minute === null ? "" : String(draft.minute).padStart(2, "0");
    }
    const period = periodOfDraft(draft);
    return period === null ? "" : periods[period];
  };

  const leave = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
      field.onLeave();
      onBlur?.();
    }
  };

  return (
    <div
      role="group"
      id={groupId}
      aria-label={labelId || id ? undefined : ariaLabel}
      aria-labelledby={labelId || id ? label : undefined}
      aria-describedby={describedBy}
      aria-disabled={disabled || undefined}
      dir="ltr"
      onBlur={leave}
      data-time-field
      data-value={value}
      className={mergeClassOverrides(
        cn(
          "inline-flex h-9 w-full min-w-0 items-center gap-0.5 rounded-lg border px-2 text-sm transition-colors",
          "focus-within:border-focus focus-within:ring-3 focus-within:ring-focus/20",
          invalid === true || invalid === "true" ? "border-danger focus-within:ring-danger/20" : "border-line-strong",
          disabled ? "cursor-not-allowed bg-surface-muted text-ink-subtle" : "bg-surface text-ink hover:border-ink-subtle",
        ),
        className,
      )}
    >
      {field.segments.map((segment, index) => {
        const segmentId = `${ownId}-${segment}`;
        const shown = shownText(segment);
        const range = segmentRange(segment, isTwelveHour);
        return (
          <span key={segment} className="inline-flex items-center">
            {segment === "minute" ? (
              <span aria-hidden className="px-px text-ink-subtle">
                :
              </span>
            ) : segment === "period" ? (
              <span aria-hidden className="w-1" />
            ) : null}
            <input
              ref={field.register(segment)}
              id={segment === "hour" && id ? id : segmentId}
              type="text"
              role="spinbutton"
              inputMode={segment === "period" ? "text" : "numeric"}
              autoComplete="off"
              spellCheck={false}
              enterKeyHint={index === field.segments.length - 1 ? "done" : "next"}
              aria-label={t(SEGMENT_NAMES[segment])}
              aria-labelledby={`${label} ${segment === "hour" && id ? id : segmentId}`}
              aria-valuenow={segmentNumber(draft, segment, isTwelveHour)}
              aria-valuemin={range.min}
              aria-valuemax={range.max}
              aria-valuetext={spoken}
              aria-invalid={invalid}
              aria-required={required || undefined}
              aria-describedby={describedBy}
              disabled={disabled}
              value={shown}
              placeholder="––"
              onKeyDown={(event) => field.onKeyDown(segment, event)}
              onChange={(event) => field.onInput(segment, event, shown)}
              onPaste={(event) => field.onPaste(segment, event)}
              onFocus={() => field.onFocus(segment)}
              className={cn(
                "h-7 rounded-md bg-transparent px-0.5 text-center tabular-nums caret-transparent outline-none",
                "placeholder:text-ink-subtle focus:bg-accent-soft focus:text-accent-ink disabled:cursor-not-allowed",
                segment === "period" ? "w-[3.25ch] uppercase" : "w-[2.6ch]",
              )}
            />
          </span>
        );
      })}
      <IconClock className="ms-auto size-4 shrink-0 text-ink-subtle" aria-hidden />
    </div>
  );
}
