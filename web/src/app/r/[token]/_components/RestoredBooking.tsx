"use client";

import { useEffect, useState } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/result";
import type { Schema } from "@/api/types";
import { bookingProblem } from "@/lib/bookingPage/refusals";
import { bookingPageTexts, hasBookingPageTexts, type BookingPageTexts } from "@/lib/bookingPage/texts";
import { directionOf, primaryLanguage } from "@/lib/hostedChat/language";

import { CustomerPageLinks } from "../../../c/[slug]/_components/CustomerPageLinks";
import { lastPageLanguage, readPageSession } from "../_lib/pageSession";
import { privacyNoticeOfView } from "../_lib/privacyNotice";
import { BookingProblemCard } from "./BookingProblemCard";
import { ManagedBooking } from "./ManagedBooking";

type View = Schema<"ManagedBookingView">;

type Restored =
  | { kind: "loading" }
  | { kind: "found"; view: View; language: string; expiresAt: number }
  | { kind: "closed"; language: string; problem: keyof BookingPageTexts };

const LINKS_CLASS = "mx-auto mt-6 w-full max-w-[560px] text-center text-sm text-ink-muted";

/** The page's language without a booking: the tab's last one, else the browser's, else English. */
function fallbackLanguage(): string {
  const remembered = lastPageLanguage();
  if (remembered && hasBookingPageTexts(remembered)) {
    return primaryLanguage(remembered);
  }
  const browser = typeof navigator === "undefined" ? "en" : navigator.language;
  return hasBookingPageTexts(browser) ? primaryLanguage(browser) : "en";
}

/** The booking of the tab's credential, or why the page cannot open it. */
async function restore(): Promise<Restored> {
  const session = readPageSession();
  if (session === null) {
    return { kind: "closed", language: fallbackLanguage(), problem: "pageClosed" };
  }
  try {
    const view = await unwrap(api.GET("/v1/public/bookings/{token}", { params: { path: { token: session.token } } }));
    const language = hasBookingPageTexts(view.language) ? primaryLanguage(view.language) : session.language;
    return { kind: "found", view, language, expiresAt: session.expiresAt };
  } catch (error) {
    const problem = bookingProblem(error);
    const shown = problem === "linkExpired" || problem === "linkInvalid" ? "pageClosed" : problem;
    return { kind: "closed", language: session.language, problem: shown };
  }
}

/**
 * /r/booking: a booking page whose link's token left the address bar
 * (pageSession.ts), reloaded in its tab. It opens the booking with the
 * tab's credential while it lasts; without one (another tab, a closed
 * one, or after about 30 minutes) it asks the guest to open the link in
 * their confirmation again.
 */
export function RestoredBooking() {
  const [restored, setRestored] = useState<Restored>({ kind: "loading" });

  useEffect(() => {
    let isCurrent = true;
    void restore().then((next) => {
      if (isCurrent) {
        setRestored(next);
      }
    });
    return () => {
      isCurrent = false;
    };
  }, []);

  if (restored.kind === "loading") {
    return <main className="bp-page" data-color-scheme="system" aria-busy="true" />;
  }
  const { language } = restored;
  const texts = bookingPageTexts(language);
  return (
    <main className="bp-page" data-color-scheme="system" lang={language} dir={directionOf(language)}>
      {restored.kind === "found" ? (
        <ManagedBooking initialView={restored.view} texts={texts} language={language} sessionExpiresAt={restored.expiresAt} />
      ) : (
        <BookingProblemCard title={texts.errorTitle} text={texts[restored.problem]} />
      )}
      <CustomerPageLinks
        language={language}
        privacyHref={restored.kind === "found" ? privacyNoticeOfView(restored.view) : null}
        // Rendered in the browser only (the server renders the loading state).
        siteOrigin={typeof window === "undefined" ? null : window.location.origin}
        className={LINKS_CLASS}
      />
    </main>
  );
}
