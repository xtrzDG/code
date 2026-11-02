import type { Metadata, Viewport } from "next";

import { bookingPageTexts } from "@/lib/bookingPage/texts";
import { directionOf } from "@/lib/hostedChat/language";
import { privacyNoticeOfChat } from "@/lib/publicSite/customerPageLinks";
import { SCHEME_BACKGROUNDS } from "@/lib/theme";
import { bookingPageLanguage, loadManagedBooking, type ManagedBookingLookup } from "@/server/managedBooking";

import { CustomerPageLinks } from "../../c/[slug]/_components/CustomerPageLinks";
import { ManagedBooking } from "./_components/ManagedBooking";

import "@/styles/bookingPage.css";
import "@/styles/bookingActions.css";

export async function generateMetadata({ params }: PageProps<"/r/[token]">): Promise<Metadata> {
  const { token } = await params;
  const lookup = await loadManagedBooking(token);
  const texts = bookingPageTexts(await bookingPageLanguage(lookup));
  return {
    title: { absolute: lookup.kind === "found" ? `${texts.pageTitle} · ${lookup.view.business_name}` : texts.errorTitle },
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

/** The business's privacy notice: the one of its chat page, when the booking names that chat. */
function privacyNoticeOf(lookup: ManagedBookingLookup): string | null {
  if (lookup.kind !== "found") {
    return null;
  }
  const chat = (lookup.view.chat_links ?? []).find((link) => link.kind === "hosted_chat");
  return chat ? privacyNoticeOfChat(chat.url) : null;
}

/**
 * /r/{token}: a guest's booking, opened from the link in their written
 * confirmation (no account). The signed token is the key; the API checks
 * it, its expiry and that the booking has not moved since, and limits how
 * often it is used. The page speaks the guest's language; at its foot the
 * business's privacy notice and the platform's accessibility statement.
 */
export default async function BookingPage({ params }: PageProps<"/r/[token]">) {
  const { token } = await params;
  const lookup = await loadManagedBooking(token);
  const language = await bookingPageLanguage(lookup);
  const texts = bookingPageTexts(language);

  return (
    <main className="bp-page" data-color-scheme="system" lang={language} dir={directionOf(language)}>
      {lookup.kind === "found" ? (
        <ManagedBooking initialView={lookup.view} texts={texts} language={language} />
      ) : (
        <article className="bp-card bp-problem-page" aria-labelledby="bp-title">
          <span className="bp-mark" aria-hidden>
            <svg viewBox="0 0 24 24" focusable="false">
              <rect x="3.5" y="5" width="17" height="15.5" rx="2.5" />
              <path d="M8 3v4M16 3v4M3.5 10h17M10 14l4 4M14 14l-4 4" />
            </svg>
          </span>
          <h1 id="bp-title" className="bp-title">
            {texts.errorTitle}
          </h1>
          <p>{texts[lookup.problem]}</p>
        </article>
      )}
      <CustomerPageLinks
        language={language}
        privacyHref={privacyNoticeOf(lookup)}
        className="mx-auto mt-6 w-full max-w-[560px] text-center text-sm text-ink-muted"
      />
    </main>
  );
}
