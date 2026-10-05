import type { Metadata } from "next";
import { headers } from "next/headers";
import { notFound, permanentRedirect } from "next/navigation";

import { getI18n } from "@/i18n/server";
import { periodLabel } from "@/lib/retentionPeriods";
import { hostedChatPath, lookUpHostedChat, type HostedChatLookup } from "@/server/hostedChat";

import { HostedChatNotice, HostedChatShell } from "../_components/HostedChatShell";
import { visitorLanguage } from "../_lib/hostedChatRequest";

async function lookUp(slug: string): Promise<HostedChatLookup> {
  return lookUpHostedChat(slug, await headers());
}

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: { absolute: t("privacyNotice.title") }, robots: { index: false, follow: false } };
}

/**
 * /c/{address}/privacy: the platform's default privacy notice for a
 * business's chat, linked from the widget's footer when the business has
 * not linked its own (Profile → links → Privacy notice). In the visitor's
 * language among the cabinet's (ka, ru, en).
 */
export default async function PrivacyNoticePage({ params }: PageProps<"/c/[slug]/privacy">) {
  const { slug } = await params;
  const [{ t, tp, locale }, lookup] = await Promise.all([getI18n(), lookUp(slug)]);
  const page = { language: locale, direction: "ltr" as const };
  if (lookup.kind === "missing") {
    notFound();
  }
  if (lookup.kind === "failed") {
    const visitor = visitorLanguage((await headers()).get("accept-language"));
    return (
      <HostedChatShell page={visitor}>
        <HostedChatNotice lead={t("privacyNotice.title")} />
      </HostedChatShell>
    );
  }

  const view = lookup.view;
  if (view.slug && view.slug !== slug) {
    permanentRedirect(`${hostedChatPath(view.slug)}/privacy`);
  }
  const values = { business: view.business_name };
  const sections = [
    { title: t("privacyNotice.whoTitle"), body: [t("privacyNotice.who", values)] },
    {
      title: t("privacyNotice.whatTitle"),
      list: [
        t("privacyNotice.whatMessages"),
        t("privacyNotice.whatContacts"),
        t("privacyNotice.whatBrowser"),
        t("privacyNotice.whatTechnical"),
      ],
    },
    { title: t("privacyNotice.whyTitle"), body: [t("privacyNotice.why", values)] },
    { title: t("privacyNotice.sharedTitle"), body: [t("privacyNotice.shared", values)] },
    {
      title: t("privacyNotice.keptTitle"),
      body: [
        // The periods the business chose in Settings → Privacy.
        t("privacyNotice.kept", {
          ...values,
          conversations: periodLabel(tp, view.conversation_retention_days),
          modelRecords: periodLabel(tp, view.llm_turn_retention_days),
        }),
      ],
    },
    { title: t("privacyNotice.rightsTitle"), body: [t("privacyNotice.rights", values)] },
  ];

  return (
    <HostedChatShell page={page} accent={view.accent_color}>
      <article className="hc-document">
        <h1>{t("privacyNotice.title")}</h1>
        <p className="hc-document-lead">{t("privacyNotice.subtitle", values)}</p>
        {sections.map((section) => (
          <section key={section.title}>
            <h2>{section.title}</h2>
            {section.body?.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            {section.list ? (
              <ul>
                {section.list.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
          </section>
        ))}
        <p className="hc-document-lead">{t("privacyNotice.platformNote", values)}</p>
        <p>
          {/* A full page load: the chat page gets its own policy from the proxy. */}
          <a href={hostedChatPath(view.slug ?? slug)}>{t("privacyNotice.backToChat")}</a>
        </p>
      </article>
    </HostedChatShell>
  );
}
