"use client";

/**
 * A calendar date in the cabinet's language: it reads "6 окт. 2026 г.",
 * "6 ოქტ. 2026" or "Oct 6, 2026" whatever the browser's own language is,
 * opens a month whose week starts where the cabinet's language starts it,
 * and keeps an ISO value ("2026-10-06"; "" for none).
 *
 *     <Field label={t("…date")}>
 *       {(control) => <DateField {...control} value={date} onChange={setDate} min={today} />}
 *     </Field>
 *
 * A date can be typed too ("06.10.2026", "10/06/2026" in English, "6 окт"):
 * it counts once it names a whole date, and what cannot be read goes back
 * to the last date on leaving the field. On a phone a tap opens the month
 * instead of the keyboard.
 */

import { useId, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";

import { IconCalendar } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { mergeClassOverrides } from "@/lib/classMerge";
import { cn } from "@/lib/cn";
import { dateText, deviceToday, parseTypedDate, type IsoDate } from "@/lib/dateInput";

import { Calendar } from "./Calendar";
import { Popover } from "./Popover";

export interface DateFieldProps {
  value: string;
  onChange: (value: string) => void;
  id?: string;
  "aria-label"?: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean | "true" | "false";
  required?: boolean;
  disabled?: boolean;
  min?: string;
  max?: string;
  /** The day the calendar marks as today (the business's); the device's day when not given. */
  today?: IsoDate;
  /** The calendar offers "Clear" (a filter's date may be empty). */
  clearable?: boolean;
  placeholder?: string;
  autoFocus?: boolean;
  className?: string;
  onBlur?: () => void;
}

/** Typed text counts at once only when it names a whole date (a 4-digit year or a month's name), not "6.10.2". */
function isWholeDate(text: string): boolean {
  return /(^|\D)\d{4}(\D|$)/.test(text) || /\p{L}{3,}/u.test(text);
}

export function DateField({
  value,
  onChange,
  id,
  "aria-label": ariaLabel,
  "aria-describedby": describedBy,
  "aria-invalid": invalid,
  required,
  disabled = false,
  min,
  max,
  today,
  clearable = false,
  placeholder,
  autoFocus,
  className,
  onBlur,
}: DateFieldProps) {
  const { t, locale } = useI18n();
  const ownId = useId();
  const calendarId = `${ownId}-calendar`;
  const anchor = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const [typed, setTyped] = useState<string | null>(null);
  const [isOpen, setOpen] = useState(false);
  const shown = typed ?? dateText(value, locale);

  const emit = (next: string) => {
    if (next !== value) {
      onChange(next);
    }
  };

  /** The typed text as a date: emitted when it is one, otherwise back to the last date. */
  const settle = () => {
    if (typed !== null) {
      const text = typed.trim();
      const parsed = text === "" ? "" : parseTypedDate(text, locale, today ?? deviceToday());
      if (parsed !== null) {
        emit(parsed);
      }
      setTyped(null);
    }
  };

  const close = (withFocus: boolean) => {
    setOpen(false);
    if (withFocus) {
      input.current?.focus();
    }
  };

  const pick = (date: string) => {
    setTyped(null);
    emit(date);
    close(true);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      settle();
      setOpen(true);
    } else if (event.key === "Escape" && isOpen) {
      event.preventDefault();
      event.stopPropagation();
      close(true);
    } else if (event.key === "Enter" && typed !== null) {
      const parsed = typed.trim() === "" ? "" : parseTypedDate(typed, locale, today ?? deviceToday());
      if (parsed !== null && parsed !== value) {
        // The date is taken first; a second Enter sends the form.
        event.preventDefault();
      }
      settle();
    }
  };

  const onPointerDown = (event: PointerEvent<HTMLInputElement>) => {
    if (event.pointerType === "touch" && !disabled) {
      event.preventDefault();
      setOpen(true);
    }
  };

  return (
    <div
      ref={anchor}
      className={mergeClassOverrides("relative w-full min-w-0", className)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null) && !isOpen) {
          onBlur?.();
        }
      }}
    >
      <input
        ref={input}
        id={id}
        type="text"
        autoComplete="off"
        spellCheck={false}
        aria-label={id ? undefined : ariaLabel}
        aria-describedby={describedBy}
        aria-invalid={invalid}
        aria-required={required || undefined}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-controls={isOpen ? calendarId : undefined}
        disabled={disabled}
        autoFocus={autoFocus}
        placeholder={placeholder ?? t("formFields.date.placeholder")}
        value={shown}
        onChange={(event) => {
          const text = event.target.value;
          setTyped(text);
          if (text.trim() === "") {
            emit("");
          } else if (isWholeDate(text)) {
            const parsed = parseTypedDate(text, locale, today ?? deviceToday());
            if (parsed !== null) {
              emit(parsed);
            }
          }
        }}
        onBlur={settle}
        onKeyDown={onKeyDown}
        onPointerDown={onPointerDown}
        className={cn(
          "block h-9 w-full rounded-lg border bg-surface pe-10 ps-3 text-sm text-ink transition-colors",
          "placeholder:text-ink-subtle hover:border-ink-subtle focus:border-focus focus:outline-none focus:ring-3 focus:ring-focus/20",
          "disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-ink-subtle",
          invalid === true || invalid === "true" ? "border-danger focus:ring-danger/20" : "border-line-strong",
        )}
      />
      <button
        type="button"
        aria-label={t("formFields.date.open")}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        disabled={disabled}
        onClick={() => {
          settle();
          setOpen((open) => !open);
        }}
        className={cn(
          "absolute inset-y-0 end-0 flex w-10 items-center justify-center rounded-e-lg text-ink-subtle transition-colors",
          "hover:text-ink focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus disabled:cursor-not-allowed",
        )}
      >
        <IconCalendar className="size-4" aria-hidden />
      </button>
      {isOpen ? (
        <Popover anchor={anchor} label={t("formFields.date.calendar")} onClose={() => close(false)}>
          <div id={calendarId}>
            <Calendar
              value={value}
              today={today ?? deviceToday()}
              min={min || undefined}
              max={max || undefined}
              onSelect={pick}
              onClear={clearable ? () => pick("") : undefined}
              onEscape={() => close(true)}
            />
          </div>
        </Popover>
      ) : null}
    </div>
  );
}
