"use client";

import { useCallback, useRef, useState } from "react";

import { BFF_BASE_PATH, api } from "@/api/client";
import { unwrap } from "@/api/result";
import type { Schema } from "@/api/types";
import { UserSentence } from "@/components/ui/UserContent";
import { interfaceSentence, type SentenceWithUserValues } from "@/i18n/userValues";
import { bookingProblem, isPageProblem, type BookingProblem } from "@/lib/bookingPage/refusals";
import type { BookingPageTexts } from "@/lib/bookingPage/texts";

import { BookingContacts } from "./BookingContacts";
import { BookingFacts } from "./BookingFacts";
import { ReschedulePanel } from "./ReschedulePanel";

type View = Schema<"ManagedBookingView">;

const STATUS_TEXT = {
  pending: "statusPending",
  confirmed: "statusConfirmed",
  cancelled: "statusCancelled",
  completed: "statusCompleted",
  no_show: "statusNoShow",
} as const satisfies Record<View["status"], keyof BookingPageTexts>;

const MOVE_PANEL_ID = "bp-move";

function CalendarIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden focusable="false">
      <rect x="3.5" y="5" width="17" height="15.5" rx="2.5" />
      <path d="M8 3v4M16 3v4M3.5 10h17M12 13.5v4M10 15.5h4" />
    </svg>
  );
}

/**
 * The guest's booking behind the link: what it is, a calendar file, a
 * move to another free time, a cancellation (confirmed in a dialog) and
 * the ways to write to the business. A move issues a new link: the page's
 * address follows it.
 */
export function ManagedBooking({
  initialView,
  texts,
  language,
}: {
  initialView: View;
  texts: BookingPageTexts;
  language: string;
}) {
  const [view, setView] = useState(initialView);
  const [notice, setNotice] = useState<SentenceWithUserValues | null>(null);
  const [problem, setProblem] = useState<BookingProblem | null>(null);
  const [isMoving, setMoving] = useState(false);
  const [isCancelling, setCancelling] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const messages = useRef<HTMLDivElement>(null);

  const isActive = view.status === "pending" || view.status === "confirmed";
  const isStale = problem !== null && isPageProblem(problem);
  const canChange = view.can_cancel && !isStale;
  const canMove = view.can_reschedule && !isStale;
  const hasStarted = isActive && !view.can_cancel && !view.is_over;
  const standing = view.is_over ? texts.overNotice : hasStarted ? texts.startedNotice : null;
  const calendarUrl = `${BFF_BASE_PATH}/v1/public/bookings/${encodeURIComponent(view.token)}/calendar.ics`;

  const report = useCallback((next: SentenceWithUserValues | null, failure: BookingProblem | null) => {
    setNotice(next);
    setProblem(failure);
    // Focus follows the outcome (the button that led here may be gone).
    requestAnimationFrame(() => messages.current?.focus());
  }, []);

  const showProblem = useCallback(
    (failure: BookingProblem | null) => {
      if (failure === null) {
        setProblem(null);
      } else {
        report(null, failure);
      }
    },
    [report],
  );

  async function cancel() {
    setCancelling(true);
    try {
      const next = await unwrap(
        api.POST("/v1/public/bookings/{token}/cancel", { params: { path: { token: view.token } } }),
      );
      setView(next);
      setMoving(false);
      report({ text: texts.cancelledNotice, values: { business: next.business_name } }, null);
    } catch (error) {
      report(null, bookingProblem(error));
    } finally {
      setCancelling(false);
      dialog.current?.close();
    }
  }

  function moved(next: View) {
    setView(next);
    setMoving(false);
    // The old link no longer opens the booking: the address takes the new one.
    window.history.replaceState(null, "", `/r/${encodeURIComponent(next.token)}`);
    report(interfaceSentence(texts.movedNotice), null);
  }

  return (
    <article className="bp-card" aria-labelledby="bp-title">
      <header className="bp-head">
        <p className="bp-business" dir="auto" data-user-content>
          {view.business_name}
        </p>
        <h1 id="bp-title" className="bp-title">
          {texts.pageTitle}
        </h1>
        <span className="bp-status" data-status={view.status}>
          {texts[STATUS_TEXT[view.status]]}
        </span>
      </header>

      <div ref={messages} className="bp-messages" tabIndex={-1} aria-live="polite">
        {notice ? (
          <p className="bp-notice">
            <UserSentence {...notice} />
          </p>
        ) : null}
        {problem ? (
          <p className="bp-problem" role="alert">
            {texts[problem]}
          </p>
        ) : null}
        {!notice && !problem && standing ? <p className="bp-notice bp-notice-quiet">{standing}</p> : null}
      </div>

      <BookingFacts view={view} texts={texts} language={language} />

      {isActive && !view.is_over ? (
        <div className="bp-actions">
          <a className="bp-button bp-button-primary" href={calendarUrl} download>
            <CalendarIcon />
            {texts.addToCalendar}
          </a>
          {canMove ? (
            <button
              type="button"
              className="bp-button"
              aria-expanded={isMoving}
              aria-controls={MOVE_PANEL_ID}
              onClick={() => setMoving((open) => !open)}
            >
              {texts.change}
            </button>
          ) : null}
          {canChange ? (
            <button type="button" className="bp-button bp-button-danger" onClick={() => dialog.current?.showModal()}>
              {texts.cancel}
            </button>
          ) : null}
        </div>
      ) : null}

      {isMoving && canMove ? (
        <ReschedulePanel
          id={MOVE_PANEL_ID}
          view={view}
          texts={texts}
          language={language}
          onMoved={moved}
          onProblem={showProblem}
          onClose={() => setMoving(false)}
        />
      ) : null}

      {view.cancellation_policy ? (
        <section className="bp-section" aria-labelledby="bp-policy-title">
          <h2 id="bp-policy-title">{texts.policy}</h2>
          <p dir="auto" data-user-content>
            {view.cancellation_policy}
          </p>
        </section>
      ) : null}

      <BookingContacts links={view.chat_links ?? []} texts={texts} />

      <dialog ref={dialog} className="bp-dialog" aria-labelledby="bp-cancel-title" aria-describedby="bp-cancel-text">
        <h2 id="bp-cancel-title">{texts.cancelTitle}</h2>
        <p id="bp-cancel-text">
          <UserSentence text={texts.cancelText} values={{ business: view.business_name }} />
        </p>
        <div className="bp-dialog-actions">
          <button type="button" className="bp-button" onClick={() => dialog.current?.close()}>
            {texts.keep}
          </button>
          <button
            type="button"
            className="bp-button bp-button-danger-solid"
            disabled={isCancelling}
            aria-busy={isCancelling}
            onClick={cancel}
          >
            {isCancelling ? texts.cancelling : texts.confirmCancel}
          </button>
        </div>
      </dialog>
    </article>
  );
}
