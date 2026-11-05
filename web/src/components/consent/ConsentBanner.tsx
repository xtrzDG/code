"use client";

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

import { IconX } from "@/components/icons";
import { Button } from "@/components/ui";

import { OPEN_COOKIE_SETTINGS_EVENT, type OpenCookieSettingsEvent } from "./consentEvents";
import { hasAnsweredHere, rememberArrival, saveConsent, type ConsentChoice } from "./saveConsent";

export interface ConsentBannerTexts {
  title: string;
  text: string;
  statementLink: string;
  statementHref: string;
  accept: string;
  reject: string;
  /** The close button's name: closing is a rejection. */
  close: string;
  failed: string;
}

function cancelFocusFrame(frame: { current: number | null }): void {
  if (frame.current !== null) {
    cancelAnimationFrame(frame.current);
    frame.current = null;
  }
}

/**
 * The public site's cookie choice (ePrivacy, the Garante's 2021
 * guidelines): a box at the foot of the screen that does not block the
 * page, with Accept and Reject side by side in the same style, and a close
 * button that rejects. It shows until the visitor answers (the server
 * renders it open while `aw_consent` holds no answer) and again from the
 * footer's "Cookie settings". After an answer focus returns to the button
 * that reopened it, if any; while it is open the page keeps focused
 * elements clear of it.
 */
export function ConsentBanner({ texts, initiallyOpen }: { texts: ConsentBannerTexts; initiallyOpen: boolean }) {
  // A page brought back from the router's cache was rendered before an answer given since.
  const [isOpen, setOpen] = useState(() => initiallyOpen && !hasAnsweredHere());
  const [isSaving, setSaving] = useState(false);
  const [hasFailed, setFailed] = useState(false);
  const opener = useRef<HTMLElement | null>(null);
  // The frame that moves focus into a reopened box, until it has run.
  const focusFrame = useRef<number | null>(null);
  const region = useRef<HTMLElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const titleId = useId();

  // The first page of the visit, for an acceptance given later on another page.
  useEffect(() => rememberArrival(), []);

  // WCAG 2.4.11: a field the keyboard reaches never hides behind the box,
  // the page scrolls it above (scroll-padding follows the box's height).
  useEffect(() => {
    const element = box.current;
    if (!isOpen || element === null) {
      return;
    }
    const root = document.documentElement;
    const pad = () => {
      root.style.scrollPaddingBottom = `${element.getBoundingClientRect().height + 24}px`;
    };
    pad();
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(pad);
    observer?.observe(element);
    return () => {
      observer?.disconnect();
      root.style.scrollPaddingBottom = "";
    };
  }, [isOpen]);

  useEffect(() => {
    const reopen = (event: Event) => {
      const named = (event as OpenCookieSettingsEvent).detail?.opener ?? null;
      opener.current = named ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null);
      setFailed(false);
      setOpen(true);
      cancelFocusFrame(focusFrame);
      focusFrame.current = requestAnimationFrame(() => {
        focusFrame.current = null;
        region.current?.focus();
      });
    };
    window.addEventListener(OPEN_COOKIE_SETTINGS_EVENT, reopen);
    return () => {
      window.removeEventListener(OPEN_COOKIE_SETTINGS_EVENT, reopen);
      cancelFocusFrame(focusFrame);
    };
  }, []);

  if (!isOpen) {
    return null;
  }

  const choose = async (choice: ConsentChoice) => {
    setSaving(true);
    const saved = await saveConsent(choice);
    setSaving(false);
    setFailed(!saved);
    if (saved) {
      // An answer given before the reopened box took focus: that frame
      // must not pull focus into a box that is closing.
      cancelFocusFrame(focusFrame);
      setOpen(false);
      opener.current?.focus();
      opener.current = null;
    }
  };
  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape" && !isSaving) {
      event.stopPropagation();
      void choose("denied");
    }
  };

  return (
    <section
      ref={region}
      tabIndex={-1}
      aria-labelledby={titleId}
      onKeyDown={onKeyDown}
      className="pointer-events-none fixed inset-x-0 bottom-0 z-50 p-3 outline-none sm:p-4"
      data-cookie-consent=""
      data-testid="cookie-consent"
    >
      {/* Only the box takes clicks: the page around it stays usable. */}
      <div ref={box} className="pointer-events-auto mx-auto w-full max-w-3xl rounded-2xl border border-line-strong bg-surface p-4 text-ink shadow-lg sm:p-5">
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1 space-y-1.5">
            <h2 id={titleId} className="text-base font-semibold text-ink">
              {texts.title}
            </h2>
            <p className="text-sm text-pretty text-ink-muted">
              {texts.text}{" "}
              <a href={texts.statementHref} className="font-medium text-accent-ink underline underline-offset-4">
                {texts.statementLink}
              </a>
            </p>
          </div>
          <button
            type="button"
            aria-label={texts.close}
            title={texts.close}
            disabled={isSaving}
            onClick={() => void choose("denied")}
            className="-me-1 -mt-1 inline-flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            <IconX className="size-4" aria-hidden />
          </button>
        </div>
        {hasFailed ? (
          <p role="alert" className="mt-3 text-sm text-danger">
            {texts.failed}
          </p>
        ) : null}
        <div className="mt-4 grid grid-cols-2 gap-2 sm:flex sm:justify-end">
          <Button variant="secondary" disabled={isSaving} onClick={() => void choose("denied")} className="sm:min-w-32">
            {texts.reject}
          </Button>
          <Button variant="secondary" disabled={isSaving} onClick={() => void choose("granted")} className="sm:min-w-32">
            {texts.accept}
          </Button>
        </div>
      </div>
    </section>
  );
}
