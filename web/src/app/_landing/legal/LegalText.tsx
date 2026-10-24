import { Alert } from "@/components/ui";
import { MarkdownDocument } from "@/components/workspace/MarkdownDocument";
import type { Translator } from "@/i18n/translate";
import { languageName } from "@/lib/format";
import { dateTimeFormat } from "@/lib/intl/formatters";

/** A version's day ("2026-10-05") in the page's language: "5 October 2026". */
function legalDay(day: string, locale: string): string {
  return dateTimeFormat(locale, { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(
    new Date(`${day}T00:00:00Z`),
  );
}

/**
 * One legal text: its title as the page's heading, a note when it is in
 * another language or a newer version is already published, then the text.
 */
export function LegalText({
  translator,
  title,
  text,
  language,
  upcomingVersion = null,
  lead = null,
}: {
  translator: Translator;
  title: string;
  text: string;
  language: string;
  upcomingVersion?: string | null;
  lead?: string | null;
}) {
  const { t, locale } = translator;
  return (
    <article className="space-y-5" data-testid="legal-text">
      <h1 className="text-3xl font-semibold tracking-tight text-balance text-ink" lang={language}>
        {title}
      </h1>
      {lead ? <p className="text-base text-pretty text-ink-muted">{lead}</p> : null}
      {language !== locale ? (
        <Alert tone="info">{t("legalPages.document.otherLanguage", { language: languageName(language, locale) })}</Alert>
      ) : null}
      {upcomingVersion ? (
        <Alert tone="info">{t("legalPages.document.upcoming", { date: legalDay(upcomingVersion, locale) })}</Alert>
      ) : null}
      <MarkdownDocument source={text} lang={language} hideTitle className="text-base" />
    </article>
  );
}
