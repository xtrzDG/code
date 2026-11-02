import type { Metadata, Viewport } from "next";

import { bookingPageTexts } from "@/lib/bookingPage/texts";
import { directionOf } from "@/lib/hostedChat/language";
import { SCHEME_BACKGROUNDS } from "@/lib/theme";
import { bookingPageLanguage, loadManagedBooking, type ManagedBookingLookup } from "@/server/managedBooking";

import { CustomerPageLinks } from "../../c/[slug]/_components/CustomerPageLinks";
import { BookingProblemCard } from "./_components/BookingProblemCard";
import { ManagedBooking } from "./_components/ManagedBooking";
import { RestoredBooking } from "./_components/RestoredBooking";
import { PAGE_SESSION_SEGMENT } from "./_lib/pageSessionPath";
import { privacyNoticeOfView } from "./_lib/privacyNotice";

import "@/styles/bookingPage.css";
import "@/styles/bookingActions.css";

/** A page opened by its credential (/r/booking) asks the API from the browser. */
const REFUSED: ManagedBookingLookup = { kind: "refused", problem: "linkInvalid" };

export async function generateMetadata({ params }: PageProps<"/r/[token]">): Promise<Metadata> {
  const { token } = await params;
  const isRestored = token === PAGE_SESSION_SEGMENT;
  const lookup = isRestored ? REFUSED : await loadManagedBooking(token);
  const texts = bookingPageTexts(await bookingPageLanguage(lookup));
  const title = lookup.kind === "found" ? `${texts.pageTitle} · ${lookup.view.business_name}` : texts.errorTitle;
  return {
    title: { absolute: isRestored ? texts.pageTitle : title },
    robots: { index: false, follow: false },
    // The address is the key to the booking: it never leaves in a Referer.
    referrer: "no-referrer",
  };
}

/** The page follows the visitor's system colours (bookingPage.css). */
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: SCHEME_BACKGROUNDS.light },
    { media: "(prefers-color-scheme: dark)", color: SCHEME_BACKGROUNDS.dark },
  ],
};

/** The business's privacy notice, when the booking could be read. */
function privacyNoticeOf(lookup: ManagedBookingLookup): string | null {
  return lookup.kind === "found" ? privacyNoticeOfView(lookup.view) : null;
}

/**
 * /r/{token}: a guest's booking, opened from the link in their written
 * confirmation (no account). The signed token is the key; the API checks
 * it, its expiry and that the booking has not moved since, and limits how
 * often it is used. Once open, the page trades the token for a short-lived
 * credential and its address becomes /r/booking (pageSession.ts), which a
 * reload of the tab opens with that credential (RestoredBooking); the link
 * itself keeps working. The page speaks the guest's language; at its foot
 * the business's privacy notice and the platform's accessibility
 * statement.
 */
export default async function BookingPage({ params }: PageProps<"/r/[token]">) {
  const { token } = await params;
  if (token === PAGE_SESSION_SEGMENT) {
    return <RestoredBooking />;
  }
  const lookup = await loadManagedBooking(token);
  const language = await bookingPageLanguage(lookup);
  const texts = bookingPageTexts(language);

  return (
    <main className="bp-page" data-color-scheme="system" lang={language} dir={directionOf(language)}>
      {lookup.kind === "found" ? (
        <ManagedBooking initialView={lookup.view} texts={texts} language={language} />
      ) : (
        <BookingProblemCard title={texts.errorTitle} text={texts[lookup.problem]} />
      )}
      <CustomerPageLinks
        language={language}
        privacyHref={privacyNoticeOf(lookup)}
        className="mx-auto mt-6 w-full max-w-[560px] text-center text-sm text-ink-muted"
      />
    </main>
  );
}
