"use client";

/**
 * The state of a TimeField: what its segments hold (complete or not), the
 * segment with the focus and the digits typed into it so far, and the keys
 * a segment answers. The value goes out as "HH:MM" once hours and minutes
 * are both there, and as "" while one is missing.
 */

import {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
  type ChangeEvent,
  type ClipboardEvent,
  type KeyboardEvent,
} from "react";

import { dayPeriods, hourCycle } from "@/lib/intl/localeCalendar";
import { minutesOf, parseTypedTime } from "@/lib/timeInput";
import {
  clearSegment,
  draftFromValue,
  draftValue,
  segmentsOf,
  stepSegment,
  typeKey,
  typeText,
  type TimeDraft,
  type TimeEditing,
  type TimeSegment,
} from "@/lib/timeSegments";

const DEFAULT_START = 9 * 60;

const wholeTime = (minutes: number): TimeDraft => ({ hour: Math.floor(minutes / 60), minute: minutes % 60, period: null });

export interface TimeFieldState {
  draft: TimeDraft;
  /** Digits typed into the focused segment and not yet whole ("1" of "17"). */
  pending: { segment: TimeSegment; buffer: string } | null;
  segments: TimeSegment[];
  register: (segment: TimeSegment) => (element: HTMLInputElement | null) => void;
  onKeyDown: (segment: TimeSegment, event: KeyboardEvent<HTMLInputElement>) => void;
  onInput: (segment: TimeSegment, event: ChangeEvent<HTMLInputElement>, shown: string) => void;
  onPaste: (segment: TimeSegment, event: ClipboardEvent<HTMLInputElement>) => void;
  onFocus: (segment: TimeSegment) => void;
  onLeave: () => void;
}

export function useTimeField({
  value,
  onChange,
  locale,
  step,
  defaultTime,
}: {
  value: string;
  onChange: (value: string) => void;
  locale: string;
  step: number;
  defaultTime?: string;
}): TimeFieldState {
  const cycle = hourCycle(locale);
  const periods = dayPeriods(locale);
  const segments = segmentsOf(cycle);
  const [draft, setDraft] = useState<TimeDraft>(() => draftFromValue(value));
  const [shownValue, setShownValue] = useState(value);
  const [pending, setPending] = useState<TimeFieldState["pending"]>(null);
  const inputs = useRef(new Map<TimeSegment, HTMLInputElement>());

  // A new value from outside (a slot picked, the form reset) replaces the draft;
  // the field's own changes come back unchanged and leave it as it is.
  if (value !== shownValue) {
    setShownValue(value);
    if (value !== draftValue(draft)) {
      setDraft(draftFromValue(value));
      setPending(null);
    }
  }

  // The focused segment's text stays selected, so the next key replaces it.
  useLayoutEffect(() => {
    const active = document.activeElement;
    for (const element of inputs.current.values()) {
      if (element === active) {
        element.select();
      }
    }
  }, [draft, pending]);

  const focus = useCallback((segment: TimeSegment) => {
    const element = inputs.current.get(segment);
    if (element && document.activeElement !== element) {
      element.focus();
    }
  }, []);

  const apply = (next: TimeEditing, from: TimeSegment) => {
    setDraft(next.draft);
    setPending(next.buffer === "" ? null : { segment: next.segment, buffer: next.buffer });
    const nextValue = draftValue(next.draft);
    setShownValue(nextValue);
    if (nextValue !== value) {
      onChange(nextValue);
    }
    if (next.segment !== from) {
      focus(next.segment);
    }
  };

  const editing = (segment: TimeSegment): TimeEditing => ({
    draft,
    segment,
    buffer: pending?.segment === segment ? pending.buffer : "",
  });

  const move = (segment: TimeSegment, offset: 1 | -1) => {
    const target = segments[segments.indexOf(segment) + offset];
    if (target) {
      setPending(null);
      focus(target);
    }
  };

  const onKeyDown = (segment: TimeSegment, event: KeyboardEvent<HTMLInputElement>) => {
    const { key } = event;
    if (event.ctrlKey || event.metaKey || event.altKey) {
      return;
    }
    if (key === "ArrowUp" || key === "ArrowDown") {
      event.preventDefault();
      const fallback = minutesOf(defaultTime ?? "") ?? DEFAULT_START;
      apply({ draft: stepSegment(draft, segment, key === "ArrowUp" ? 1 : -1, { step, fallback }), segment, buffer: "" }, segment);
    } else if (key === "ArrowLeft" || key === "ArrowRight") {
      event.preventDefault();
      move(segment, key === "ArrowRight" ? 1 : -1);
    } else if (key === "Backspace" || key === "Delete") {
      event.preventDefault();
      const isEmpty = segment === "hour" ? draft.hour === null : segment === "minute" ? draft.minute === null : true;
      if (isEmpty && key === "Backspace") {
        move(segment, -1);
      } else {
        apply({ draft: clearSegment(draft, segment), segment, buffer: "" }, segment);
      }
    } else if (key.length === 1) {
      event.preventDefault();
      apply(typeKey(editing(segment), key, cycle, periods), segment);
    }
  };

  /**
   * Text that reached the segment without a key it could read: a phone's
   * keyboard, the browser filling the field, a test typing into it. The
   * segment's text is selected on focus, so what is there is what was typed.
   */
  const onInput = (segment: TimeSegment, event: ChangeEvent<HTMLInputElement>, shown: string) => {
    const text = event.target.value;
    const typed = shown !== "" && text.startsWith(shown) ? text.slice(shown.length) : text;
    if (typed === "") {
      apply({ draft: clearSegment(draft, segment), segment, buffer: "" }, segment);
      return;
    }
    const whole = parseTypedTime(typed, locale);
    if (whole !== null && /\D/.test(typed.trim())) {
      apply({ draft: wholeTime(whole), segment, buffer: "" }, segment);
      return;
    }
    apply(typeText(editing(segment), typed, cycle, periods), segment);
  };

  const onPaste = (segment: TimeSegment, event: ClipboardEvent<HTMLInputElement>) => {
    const text = event.clipboardData.getData("text");
    const whole = parseTypedTime(text, locale);
    event.preventDefault();
    if (whole !== null) {
      apply({ draft: wholeTime(whole), segment, buffer: "" }, segment);
    } else {
      apply(typeText(editing(segment), text, cycle, periods), segment);
    }
  };

  const register = useCallback(
    (segment: TimeSegment) => (element: HTMLInputElement | null) => {
      if (element) {
        inputs.current.set(segment, element);
      } else {
        inputs.current.delete(segment);
      }
    },
    [],
  );

  return {
    draft,
    pending,
    segments,
    register,
    onKeyDown,
    onInput,
    onPaste,
    onFocus: (segment) => {
      if (pending && pending.segment !== segment) {
        setPending(null);
      }
      inputs.current.get(segment)?.select();
    },
    onLeave: () => setPending(null),
  };
}
