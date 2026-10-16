import type { Schema } from "@/api/types";
import type { BookingPageTexts } from "@/lib/bookingPage/texts";

type ContactLink = Schema<"WidgetContactLinkView">;

/** Only web and phone links leave the page. */
const SAFE_LINK = /^(https?:\/\/|tel:)/i;

const BRAND_NAMES: Readonly<Partial<Record<ContactLink["kind"], string>>> = {
  whatsapp: "WhatsApp",
  telegram: "Telegram",
  messenger: "Messenger",
  instagram: "Instagram",
};

function labelOf(link: ContactLink, texts: BookingPageTexts): string {
  if (link.kind === "hosted_chat") {
    return texts.chat;
  }
  if (link.kind === "phone") {
    return texts.call;
  }
  return BRAND_NAMES[link.kind] ?? texts.chat;
}

function ContactIcon({ kind }: { kind: ContactLink["kind"] }) {
  return kind === "phone" ? (
    <svg viewBox="0 0 24 24" aria-hidden focusable="false">
      <path d="M5 4h4l2 5-2.5 1.5a11 11 0 005 5L15 13l5 2v4a2 2 0 01-2 2A16 16 0 013 6a2 2 0 012-2z" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" aria-hidden focusable="false">
      <path d="M5 18l-1.5 3 4-1.5A8.5 8.5 0 1012 3.5 8.5 8.5 0 003.5 12c0 2.2.6 4.2 1.5 6z" />
    </svg>
  );
}

/**
 * "Write to us": the chat the booking was made in first, then the
 * business's other chats and a call (the API orders them).
 */
export function BookingContacts({ links, texts }: { links: readonly ContactLink[]; texts: BookingPageTexts }) {
  const usable = links.filter((link) => SAFE_LINK.test(link.url));
  if (usable.length === 0) {
    return null;
  }
  return (
    <section className="bp-section" aria-labelledby="bp-contacts-title">
      <h2 id="bp-contacts-title">{texts.writeToUs}</h2>
      <ul className="bp-contacts">
        {usable.map((link) => (
          <li key={`${link.kind}:${link.url}`}>
            <a
              className="bp-button"
              href={link.url}
              {...(link.kind === "phone" ? {} : { target: "_blank", rel: "noopener noreferrer" })}
            >
              <ContactIcon kind={link.kind} />
              {labelOf(link, texts)}
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
