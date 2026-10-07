import type { Metadata } from "next";
import { headers } from "next/headers";
import { notFound, permanentRedirect } from "next/navigation";

import { UserSentence } from "@/components/ui/UserContent";
import { isLocale } from "@/i18n/config";
import { FALLBACK_MESSAGES, getMessages } from "@/i18n/messages";
import { createTranslator, type MessageValues } from "@/i18n/translate";
import type { SentenceWithUserValues } from "@/i18n/userValues";
import { directionOf } from "@/lib/hostedChat/language";
import { daysLabel, periodLabel } from "@/lib/retentionPeriods";
import { hostedChatPath, lookUpHostedChat, type HostedChatLookup, type HostedChatView } from "@/server/hostedChat";

import { HostedChatNotice, HostedChatShell } from "../_components/HostedChatShell";
import { chatLanguage, visitorLanguage, type PageLanguage } from "../_lib/hostedChatRequest";
import { PRIVACY_NOTICE_DRAFTS, privacyNoticeFor } from "./_texts/privacyNoticeTexts";

const REVIEWED_LANGUAGES = ["en", "ru", "ka"];

async function lookUp(slug: string): Promise<HostedChatLookup> {
  return lookUpHostedChat(slug, await headers());
}

/** `?lang=en` (the draft's "Read in English" link) when the notice has that language. */
function requestedLanguage(raw: string | string[] | undefined): PageLanguage | null {
  const tag = typeof raw === "string" ? raw.trim().toLowerCase() : "";
  if (!REVIEWED_LANGUAGES.includes(tag) && !(tag in PRIVACY_NOTICE_DRAFTS)) {
    return null;
  }
  return { language: tag, direction: directionOf(tag) };
}

/**
 * The periods the business chose in Settings → Privacy, named in a reviewed
 * language; a draft's "How long" names none, so it needs no values.
 */
function keptPeriods(language: string, view: HostedChatView): MessageValues {
  if (!isLocale(language)) {
    return {};
  }
  const { tp } = createTranslator(language, getMessages(language), FALLBACK_MESSAGES);
  return {
    conversations: periodLabel(tp, view.conversation_retention_days),
    modelRecords: daysLabel(tp, view.llm_turn_retention_days),
  };
}

export async function generateMetadata({ searchParams }: PageProps<"/c/[slug]/privacy">): Promise<Metadata> {
  const visitor =
    requestedLanguage((await searchParams).lang) ?? visitorLanguage((await headers()).get("accept-language"));
  return {
    title: { absolute: privacyNoticeFor(visitor.language).text("title") },
    robots: { index: false, follow: false },
  };
}

/**
 * /c/{address}/privacy: the platform's default privacy notice for a
 * business's chat, linked from the widget's footer when the business has
 * not linked its own (Profile → links → Privacy notice). In the visitor's
 * language among the business's customer languages, as the chat itself:
 * the reviewed texts in English, Russian and Georgian, a draft marked for
 * review (with a link to the English text, which prevails) in the other
 * languages of the chat widget.
 */
export default async function PrivacyNoticePage({ params, searchParams }: PageProps<"/c/[slug]/privacy">) {
  const { slug } = await params;
  const [query, lookup, incoming] = await Promise.all([searchParams, lookUp(slug), headers()]);
  const acceptLanguage = incoming.get("accept-language");
  if (lookup.kind === "missing") {
    notFound();
  }
  if (lookup.kind === "failed") {
    const visitor = visitorLanguage(acceptLanguage);
    return (
      <HostedChatShell page={visitor}>
        <HostedChatNotice lead={privacyNoticeFor(visitor.language).text("title")} />
      </HostedChatShell>
    );
  }

  const view = lookup.view;
  if (view.slug && view.slug !== slug) {
    permanentRedirect(`${hostedChatPath(view.slug)}/privacy`);
  }
  const chosen = requestedLanguage(query.lang) ?? chatLanguage(view, acceptLanguage);
  const notice = privacyNoticeFor(chosen.language);
  const page: PageLanguage = { language: notice.language, direction: directionOf(notice.language) };
  const text = notice.text;
  // The business's name is user content: each sentence keeps its placeholder and `UserSentence` shows it.
  const names = { business: view.business_name };
  const naming = (key: Parameters<typeof text>[0], values?: MessageValues): SentenceWithUserValues => ({ text: text(key, values), values: names });
  const sections = [
    { title: text("whoTitle"), body: [naming("who")] },
    {
      title: text("whatTitle"),
      list: [text("whatMessages"), text("whatContacts"), text("whatBrowser"), text("whatTechnical")],
    },
    { title: text("whyTitle"), body: [naming("why")] },
    { title: text("sharedTitle"), body: [naming("shared")] },
    { title: text("keptTitle"), body: [naming("kept", keptPeriods(notice.language, view))] },
    { title: text("rightsTitle"), body: [naming("rights")] },
  ];
  const address = hostedChatPath(view.slug ?? slug);

  return (
    <HostedChatShell page={page} accent={view.accent_color}>
      <article className="hc-document">
        <h1>{text("title")}</h1>
        <p className="hc-document-lead">
          <UserSentence {...naming("subtitle")} />
        </p>
        {notice.needsReview ? (
          <p className="hc-document-draft" role="note" data-testid="privacy-draft-note">
            {text("draftNote")}{" "}
            <a href={`${address}/privacy?lang=en`} hrefLang="en">
              {text("readInEnglish")}
            </a>
          </p>
        ) : null}
        {sections.map((section) => (
          <section key={section.title}>
            <h2>{section.title}</h2>
            {section.body?.map((paragraph) => (
              <p key={paragraph.text}>
                <UserSentence {...paragraph} />
              </p>
            ))}
            {section.list ? (
              <ul>
                {section.list.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
          </section>
        ))}
        <p className="hc-document-lead">
          <UserSentence {...naming("platformNote")} />
        </p>
        <p>
          {/* A full page load: the chat page gets its own policy from the proxy. */}
          <a href={address}>{text("backToChat")}</a>
        </p>
      </article>
    </HostedChatShell>
  );
}
