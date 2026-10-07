"use client";

import { useEffect, useMemo, useState } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/result";
import type { Schema } from "@/api/types";
import { DateField } from "@/components/ui/DateField";
import { DateFieldLanguage } from "@/components/ui/DateFieldLanguage";
import { bookingDateTexts } from "@/lib/bookingPage/dateTexts";
import { fillPlaceholders, formatLocalTime, moveTarget, todayIn, wallClock } from "@/lib/bookingPage/format";
import { bookingProblem, type BookingProblem } from "@/lib/bookingPage/refusals";
import type { BookingPageTexts } from "@/lib/bookingPage/texts";

type View = Schema<"ManagedBookingView">;
type Slots = Schema<"ManagedBookingSlots">;

/** The free times of one date, or why there are none. */
function SlotChoice({
  slots,
  view,
  chosen,
  onChoose,
  texts,
  language,
}: {
  slots: Slots;
  view: View;
  chosen: string | null;
  onChoose: (time: string) => void;
  texts: BookingPageTexts;
  language: string;
}) {
  if (!slots.is_open_on_date) {
    return <p className="bp-hint">{texts.closedDay}</p>;
  }
  if (slots.booking_unit === "night") {
    return <p className="bp-hint">{slots.is_stay_available ? texts.stayFree : texts.stayTaken}</p>;
  }
  // The booking's own start is no move.
  const times = (slots.times ?? []).filter((time) => !(slots.date === view.date && time === view.time));
  if (times.length === 0) {
    return <p className="bp-hint">{texts.noTimes}</p>;
  }
  return (
    <fieldset className="bp-times">
      <legend>{texts.freeTimes}</legend>
      {times.map((time) => (
        <button
          key={time}
          type="button"
          className="bp-time-option"
          aria-pressed={chosen === time}
          onClick={() => onChoose(time)}
        >
          {formatLocalTime(time, language)}
        </button>
      ))}
    </fieldset>
  );
}

/**
 * "Choose a new time": a date (from today in the business's zone, in the
 * UI kit's date field speaking the page's language), its free times (or,
 * for a stay, whether its nights are free from that date) and the move.
 * Only a free time can be chosen; the API checks it again under the
 * booking's lock, and a time taken meanwhile reloads the day's free times.
 */
export function ReschedulePanel({
  id,
  view,
  texts,
  language,
  onMoved,
  onProblem,
  onClose,
}: {
  id: string;
  view: View;
  texts: BookingPageTexts;
  language: string;
  onMoved: (next: View) => void;
  onProblem: (problem: BookingProblem | null) => void;
  onClose: () => void;
}) {
  const today = useMemo(() => todayIn(view.timezone, new Date()), [view.timezone]);
  const [date, setDate] = useState(() => (view.date >= today ? view.date : today));
  const [round, setRound] = useState(0);
  const [slots, setSlots] = useState<Slots | null>(null);
  const [failedDate, setFailedDate] = useState<string | null>(null);
  const [chosen, setChosen] = useState<string | null>(null);
  const [isSaving, setSaving] = useState(false);
  const dateTexts = useMemo(() => bookingDateTexts(language), [language]);
  const isStay = view.booking_unit === "night";
  const isValidDate = wallClock(date) !== null && date >= today;
  const isPast = wallClock(date) !== null && date < today;

  useEffect(() => {
    if (!isValidDate) {
      return undefined;
    }
    const controller = new AbortController();
    unwrap(
      api.GET("/v1/public/bookings/{token}/slots", {
        params: { path: { token: view.token }, query: { date } },
        signal: controller.signal,
      }),
    ).then(
      (answer) => {
        if (!controller.signal.aborted) {
          setSlots(answer);
        }
      },
      (error: unknown) => {
        if (!controller.signal.aborted) {
          setFailedDate(date);
          onProblem(bookingProblem(error));
        }
      },
    );
    return () => controller.abort();
  }, [date, round, isValidDate, view.token, onProblem]);

  const answer = slots !== null && slots.date === date ? slots : null;
  const isLoading = isValidDate && answer === null && failedDate !== date;
  const isReady = answer !== null && (isStay ? answer.is_stay_available : chosen !== null);

  function pickDate(next: string) {
    setDate(next);
    setChosen(null);
    setSlots(null);
    setFailedDate(null);
    onProblem(null);
  }

  async function move() {
    setSaving(true);
    onProblem(null);
    try {
      const next = await unwrap(
        api.POST("/v1/public/bookings/{token}/reschedule", {
          params: { path: { token: view.token } },
          body: { date, time: isStay ? null : chosen },
        }),
      );
      onMoved(next);
    } catch (error) {
      onProblem(bookingProblem(error));
      setChosen(null);
      setSlots(null);
      setRound((value) => value + 1);
      setSaving(false);
    }
  }

  const target = moveTarget(date, isStay ? null : chosen, language);
  return (
    <section id={id} className="bp-panel" aria-labelledby={`${id}-title`}>
      <h2 id={`${id}-title`}>{texts.newTime}</h2>
      <div className="bp-field">
        <label htmlFor={`${id}-date`}>{texts.date}</label>
        <DateFieldLanguage locale={language} texts={dateTexts}>
          <DateField
            id={`${id}-date`}
            value={date}
            min={today}
            today={today}
            required
            aria-invalid={isPast || undefined}
            aria-describedby={isPast ? `${id}-date-hint` : undefined}
            onChange={pickDate}
          />
        </DateFieldLanguage>
        {isPast ? (
          <p id={`${id}-date-hint`} className="bp-field-hint">
            {dateTexts.pastDate}
          </p>
        ) : null}
      </div>
      <div className="bp-slots" aria-live="polite" aria-busy={isLoading}>
        {isLoading ? <p className="bp-hint">{texts.loadingTimes}</p> : null}
        {answer ? (
          <SlotChoice
            slots={answer}
            view={view}
            chosen={chosen}
            onChoose={setChosen}
            texts={texts}
            language={language}
          />
        ) : null}
      </div>
      <div className="bp-panel-actions">
        <button
          type="button"
          className="bp-button bp-button-primary"
          disabled={!isReady || isSaving}
          aria-busy={isSaving}
          onClick={move}
        >
          {isSaving ? texts.moving : fillPlaceholders(texts.moveTo, { when: target })}
        </button>
        <button type="button" className="bp-button bp-button-quiet" onClick={onClose}>
          {texts.close}
        </button>
      </div>
    </section>
  );
}
