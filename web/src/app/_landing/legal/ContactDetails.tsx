import type { ComponentType } from "react";

import { IconExternal, IconMail, IconShield, IconTelegram, IconWhatsApp, type IconProps } from "@/components/icons";
import type { Translator } from "@/i18n/translate";
import { countryName } from "@/lib/countries";

import type { LegalOverview, SupportContacts } from "./legalData";

type Operator = LegalOverview["operator"];

interface Channel {
  key: string;
  label: string;
  detail: string;
  href: string;
  icon: ComponentType<IconProps>;
  external: boolean;
}

function supportChannels(t: Translator["t"], contacts: SupportContacts | null): Channel[] {
  if (!contacts) {
    return [];
  }
  const channels: Channel[] = [];
  if (contacts.whatsapp_url && contacts.whatsapp_number) {
    channels.push({ key: "whatsapp", label: t("legalPages.supportWhatsApp"), detail: contacts.whatsapp_number, href: contacts.whatsapp_url, icon: IconWhatsApp, external: true });
  }
  if (contacts.telegram_url && contacts.telegram_username) {
    channels.push({ key: "telegram", label: t("legalPages.supportTelegram"), detail: `@${contacts.telegram_username}`, href: contacts.telegram_url, icon: IconTelegram, external: true });
  }
  if (contacts.email_url && contacts.email) {
    channels.push({ key: "email", label: t("legalPages.supportEmail"), detail: contacts.email, href: contacts.email_url, icon: IconMail, external: false });
  }
  return channels;
}

/**
 * The contact page's body: the support channels the platform has set up,
 * the operator's details as the invoices name the seller (a missing
 * address says it comes before the opening), and where security
 * researchers report a vulnerability.
 */
export function ContactDetails({
  translator,
  operator,
  contacts,
}: {
  translator: Translator;
  operator: Operator | null;
  contacts: SupportContacts | null;
}) {
  const { t, locale } = translator;
  const channels = supportChannels(t, contacts);
  const rows: [string, string | null | undefined][] = operator
    ? [
        [t("legalPages.legalName"), operator.legal_name],
        [t("legalPages.address"), operator.address],
        [t("legalPages.taxId"), operator.tax_id],
        [t("legalPages.country"), countryName(operator.country_code, locale)],
        [t("legalPages.email"), operator.email],
      ]
    : [];
  const card = "rounded-2xl border border-line bg-surface p-6";

  return (
    <div className="space-y-6" data-testid="contact-details">
      <div className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight text-ink">{t("legalPages.contactTitle")}</h1>
        <p className="text-base text-pretty text-ink-muted">{t("legalPages.contactLead")}</p>
      </div>
      <section aria-labelledby="support-title" className={card}>
        <h2 id="support-title" className="text-base font-semibold text-ink">
          {t("legalPages.supportTitle")}
        </h2>
        {channels.length > 0 ? (
          <ul className="mt-4 space-y-2">
            {channels.map(({ key, label, detail, href, icon: Icon, external }) => (
              <li key={key}>
                <a
                  href={href}
                  {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                  className="flex items-center gap-3 rounded-xl border border-line px-4 py-3 text-sm transition-colors hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus"
                >
                  <Icon className="size-4 shrink-0 text-accent" aria-hidden />
                  <span className="font-medium text-ink">{label}</span>
                  <span className="min-w-0 truncate text-ink-muted">{detail}</span>
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-ink-muted">{t("legalPages.supportMissing")}</p>
        )}
      </section>
      <section aria-labelledby="operator-title" className={card}>
        <h2 id="operator-title" className="text-base font-semibold text-ink">
          {t("legalPages.operatorTitle")}
        </h2>
        {rows.length > 0 ? (
          <dl className="mt-4 grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[10rem_minmax(0,1fr)]">
            {rows
              .filter((row): row is [string, string] => Boolean(row[1]))
              .map(([label, value]) => (
                <div key={label} className="contents">
                  <dt className="text-ink-subtle">{label}</dt>
                  <dd className="break-words text-ink">{value}</dd>
                </div>
              ))}
          </dl>
        ) : null}
        {!operator?.address ? <p className="mt-4 text-sm text-ink-muted">{t("legalPages.operatorMissing")}</p> : null}
      </section>
      <section aria-labelledby="report-title" className={card}>
        <h2 id="report-title" className="flex items-center gap-2 text-base font-semibold text-ink">
          <IconShield className="size-4 text-accent" aria-hidden />
          {t("legalPages.securityReportTitle")}
        </h2>
        <p className="mt-2 text-sm text-ink-muted">{t("legalPages.securityReportText")}</p>
        <a
          href="/.well-known/security.txt"
          className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-accent underline-offset-4 hover:underline"
        >
          {t("legalPages.securityReportLink")}
          <IconExternal className="size-3.5" aria-hidden />
        </a>
      </section>
    </div>
  );
}
