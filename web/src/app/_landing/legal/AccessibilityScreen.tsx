import Link from "next/link";
import { notFound } from "next/navigation";

import { isCabinetLanguage } from "@/i18n/config";
import { getI18n } from "@/i18n/server";
import { dateTimeFormat } from "@/lib/intl/formatters";
import { legalPath } from "@/lib/publicSite/paths";

import { ACCESSIBILITY_LIMITATIONS, ACCESSIBILITY_STATEMENT_DATE, AGID_REPORT_URL } from "./accessibilityStatement";
import { loadLegalOverview, loadSupportContacts } from "./legalData";
import { LegalShell } from "./LegalShell";

const SECTION = "space-y-2";
const HEADING = "text-xl font-semibold text-ink";
const LINK = "font-medium text-accent-ink underline underline-offset-4";

/**
 * "/it/accessibility": the accessibility statement, after AgID's model:
 * what it covers, the compliance status (WCAG 2.2 AA, partially
 * compliant), the known limitations, how it was prepared and when, how to
 * report a barrier (the platform's support e-mail, else the contact page)
 * and the enforcement procedure (AgID). Its texts are the dictionary's
 * (`accessibility.*`), so it reads in every cabinet language.
 */
export async function AccessibilityScreen({ locale }: { locale: string }) {
  if (!isCabinetLanguage(locale)) {
    notFound();
  }
  const [{ t }, overview, contacts] = await Promise.all([getI18n(), loadLegalOverview(), loadSupportContacts()]);
  const operator = overview?.operator?.legal_name || t("accessibility.operatorFallback");
  const email = contacts?.email || overview?.operator?.email || null;
  const date = dateTimeFormat(locale, { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(
    new Date(`${ACCESSIBILITY_STATEMENT_DATE}T00:00:00Z`),
  );

  return (
    <LegalShell t={t} locale={locale} page="accessibility" isDraft={false}>
      <article className="space-y-6 text-base leading-relaxed text-ink-muted" data-testid="accessibility-statement">
        <div className="space-y-3">
          <h1 className="text-3xl font-semibold tracking-tight text-balance text-ink">{t("accessibility.title")}</h1>
          <p className="text-pretty">{t("accessibility.lead", { operator })}</p>
          <p className="text-pretty">{t("accessibility.basis")}</p>
        </div>
        <section className={SECTION}>
          <h2 className={HEADING}>{t("accessibility.statusTitle")}</h2>
          <p className="text-pretty">{t("accessibility.statusText")}</p>
        </section>
        <section className={SECTION}>
          <h2 className={HEADING}>{t("accessibility.limitationsTitle")}</h2>
          <ul className="list-disc space-y-1.5 ps-5">
            {ACCESSIBILITY_LIMITATIONS.map((item) => (
              <li key={item}>{t(`accessibility.limitations.${item}`)}</li>
            ))}
          </ul>
        </section>
        <section className={SECTION}>
          <h2 className={HEADING}>{t("accessibility.methodTitle")}</h2>
          <p className="text-pretty">{t("accessibility.methodText")}</p>
          <p className="text-pretty">{t("accessibility.dateText", { date })}</p>
        </section>
        <section className={SECTION}>
          <h2 className={HEADING}>{t("accessibility.feedbackTitle")}</h2>
          <p className="text-pretty">{t("accessibility.feedbackText")}</p>
          <p>
            {email ? (
              <a href={`mailto:${email}`} className={LINK}>
                {t("accessibility.feedbackEmail", { email })}
              </a>
            ) : (
              <>
                {t("accessibility.feedbackContact")}{" "}
                <Link href={legalPath(locale, "contact")} className={LINK}>
                  {t("accessibility.contactLink")}
                </Link>
              </>
            )}
          </p>
        </section>
        <section className={SECTION}>
          <h2 className={HEADING}>{t("accessibility.enforcementTitle")}</h2>
          <p className="text-pretty">{t("accessibility.enforcementText")}</p>
          <p>
            <a href={AGID_REPORT_URL} target="_blank" rel="noopener noreferrer" className={LINK}>
              {t("accessibility.enforcementLink")}
            </a>
          </p>
        </section>
        <section className={SECTION}>
          <h2 className={HEADING}>{t("accessibility.technologiesTitle")}</h2>
          <p className="text-pretty">{t("accessibility.technologiesText")}</p>
        </section>
      </article>
    </LegalShell>
  );
}
