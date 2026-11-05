"use client";

/**
 * A date and a time under one label (an incident's start, an
 * announcement's expected end), in the cabinet's language. The value is
 * "YYYY-MM-DDTHH:MM" (what `<input type="datetime-local">` held), "" when
 * both are empty, and a half value ("2026-10-06T", "T08:30") while only one
 * is filled, so the form's own check says the time is incomplete.
 */

import { useState } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { DateField } from "./DateField";
import { fieldLabelId } from "./Field";
import { TimeField } from "./TimeField";

const DATE_TIME = /^(\d{4}-\d{2}-\d{2})?T(\d{2}:\d{2})?$/;

function partsOf(value: string): { date: string; time: string } {
  const match = DATE_TIME.exec(value);
  return { date: match?.[1] ?? "", time: match?.[2] ?? "" };
}

export function DateTimeField({
  value,
  onChange,
  id,
  "aria-describedby": describedBy,
  "aria-invalid": invalid,
  required,
  disabled = false,
  min,
  max,
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  /** From a Field: the date takes it; the time is labelled by the same label. */
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean | "true" | "false";
  required?: boolean;
  disabled?: boolean;
  /** Bounds of the date part ("YYYY-MM-DD"). */
  min?: string;
  max?: string;
  className?: string;
}) {
  const { t } = useI18n();
  const [parts, setParts] = useState(() => partsOf(value));
  const [shownValue, setShownValue] = useState(value);
  const joined = (next: { date: string; time: string }) => (next.date === "" && next.time === "" ? "" : `${next.date}T${next.time}`);

  if (value !== shownValue) {
    setShownValue(value);
    if (value !== joined(parts)) {
      setParts(partsOf(value));
    }
  }

  const update = (change: Partial<{ date: string; time: string }>) => {
    const next = { ...parts, ...change };
    setParts(next);
    const nextValue = joined(next);
    setShownValue(nextValue);
    if (nextValue !== value) {
      onChange(nextValue);
    }
  };

  return (
    <div className={cn("flex flex-wrap gap-2 sm:flex-nowrap", className)}>
      <DateField
        id={id}
        className="min-w-40 flex-[3]"
        value={parts.date}
        onChange={(date) => update({ date })}
        aria-describedby={describedBy}
        aria-invalid={invalid}
        required={required}
        disabled={disabled}
        min={min}
        max={max}
        placeholder={t("formFields.date.date")}
      />
      <TimeField
        labelId={fieldLabelId(id)}
        className="min-w-28 flex-[2]"
        value={parts.time}
        onChange={(time) => update({ time })}
        aria-describedby={describedBy}
        aria-invalid={invalid}
        required={required}
        disabled={disabled}
      />
    </div>
  );
}
