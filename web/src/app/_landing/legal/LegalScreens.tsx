import { notFound } from "next/navigation";

import { getI18n } from "@/i18n/server";
import { isCabinetLanguage } from "@/i18n/config";
import type { Translator } from "@/i18n/translate";

import { ContactDetails } from "./ContactDetails";
import { loadDpaText, loadLegalOverview, loadLegalText, loadSupportContacts, type LegalTextKind } from "./legalData";
import { LegalShell } from "./LegalShell";
import { LegalText } from "./LegalText";

function Unavailable({ t }: { t: Translator["t"] }) {
  return (
    <p className="rounded-2xl border border-line bg-surface p-6 text-sm text-ink-muted" role="status">
      {t("legalPages.unavailable")}
    </p>
  );
}

/** "/ru/terms", "/ka/privacy", "/en/security": the text in force, from GET /v1/legal/{kind}. */
export async function LegalDocumentScreen({ locale, kind }: { locale: string; kind: LegalTextKind }) {
  if (!isCabinetLanguage(locale)) {
    notFound();
  }
  const [translator, overview, document] = await Promise.all([getI18n(), loadLegalOverview(), loadLegalText(kind, locale)]);
  const isDraft = (overview?.is_draft ?? true) || (document?.is_draft ?? false);
  return (
    <LegalShell t={translator.t} locale={locale} page={kind} isDraft={isDraft}>
      {document ? (
        <LegalText
          translator={translator}
          title={document.title}
          text={document.text}
          language={document.language}
          upcomingVersion={document.upcoming_version ?? null}
        />
      ) : (
        <Unavailable t={translator.t} />
      )}
    </LegalShell>
  );
}

/** "/ru/dpa": the data processing agreement in force (DPA_DOCUMENT_VERSION). */
export async function DpaScreen({ locale }: { locale: string }) {
  if (!isCabinetLanguage(locale)) {
    notFound();
  }
  const [translator, overview] = await Promise.all([getI18n(), loadLegalOverview()]);
  const dpa = overview ? await loadDpaText(overview.dpa_version, locale) : null;
  return (
    <LegalShell t={translator.t} locale={locale} page="dpa" isDraft={overview?.is_draft ?? true}>
      {dpa ? (
        <LegalText
          translator={translator}
          title={dpa.title}
          text={dpa.text}
          language={dpa.language}
          lead={translator.t("legalPages.dpaLead")}
        />
      ) : (
        <Unavailable t={translator.t} />
      )}
    </LegalShell>
  );
}

/** "/ru/contact": who provides the service and how to reach a person. */
export async function ContactScreen({ locale }: { locale: string }) {
  if (!isCabinetLanguage(locale)) {
    notFound();
  }
  const [translator, overview, contacts] = await Promise.all([getI18n(), loadLegalOverview(), loadSupportContacts()]);
  return (
    <LegalShell t={translator.t} locale={locale} page="contact" isDraft={overview?.is_draft ?? true}>
      <ContactDetails translator={translator} operator={overview?.operator ?? null} contacts={contacts} />
    </LegalShell>
  );
}
