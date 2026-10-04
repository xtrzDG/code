"use client";

/**
 * How to reach the platform's support (SUPPORT_WHATSAPP, SUPPORT_TELEGRAM,
 * SUPPORT_EMAIL on the API): the channels that are set, as links that open
 * the chat or the mail app. Nothing is shown while none is set.
 */

import type { ComponentType } from "react";

import { IconMail, IconTelegram, IconWhatsApp, type IconProps } from "@/components/icons";
import { buttonClasses } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { cn } from "@/lib/cn";

import { useSupportContacts, type SupportContacts as Contacts } from "./useHelp";

interface ContactLink {
  key: "whatsapp" | "telegram" | "email";
  label: MessageKey;
  icon: ComponentType<IconProps>;
  href: string;
  /** What the link shows besides its name: the number, the @username, the address. */
  detail: string;
  external: boolean;
}

export function contactLinks(contacts: Contacts | undefined): ContactLink[] {
  if (!contacts) {
    return [];
  }
  const links: ContactLink[] = [];
  if (contacts.whatsapp_url && contacts.whatsapp_number) {
    links.push({ key: "whatsapp", label: "helpCenter.support.whatsapp", icon: IconWhatsApp, href: contacts.whatsapp_url, detail: contacts.whatsapp_number, external: true });
  }
  if (contacts.telegram_url && contacts.telegram_username) {
    links.push({ key: "telegram", label: "helpCenter.support.telegram", icon: IconTelegram, href: contacts.telegram_url, detail: `@${contacts.telegram_username}`, external: true });
  }
  if (contacts.email_url && contacts.email) {
    links.push({ key: "email", label: "helpCenter.support.email", icon: IconMail, href: contacts.email_url, detail: contacts.email, external: false });
  }
  return links;
}

/**
 * `rows`: one row per channel with its detail (the account panel, the help
 * center); `buttons`: small buttons in a row (the article drawer).
 */
export function SupportContacts({ variant = "rows", rowClassName }: { variant?: "rows" | "buttons"; rowClassName?: string }) {
  const { t } = useI18n();
  const contacts = useSupportContacts();
  const links = contactLinks(contacts.data);
  if (links.length === 0) {
    return null;
  }

  if (variant === "buttons") {
    return (
      <ul className="flex flex-wrap gap-2" aria-label={t("helpCenter.support.contact")}>
        {links.map((link) => (
          <li key={link.key}>
            <a
              href={link.href}
              target={link.external ? "_blank" : undefined}
              rel={link.external ? "noopener noreferrer" : undefined}
              className={buttonClasses({ variant: "secondary", size: "sm" })}
            >
              <link.icon className="size-4" aria-hidden />
              <span>{t(link.label)}</span>
              {link.external ? <span className="sr-only"> ({t("helpCenter.opensInNewTab")})</span> : null}
            </a>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <ul className="space-y-0.5" aria-label={t("helpCenter.support.contact")}>
      {links.map((link) => (
        <li key={link.key}>
          <a
            href={link.href}
            target={link.external ? "_blank" : undefined}
            rel={link.external ? "noopener noreferrer" : undefined}
            className={cn(rowClassName)}
          >
            <link.icon className="size-4 shrink-0" aria-hidden />
            <span className="min-w-0">
              <span className="block font-medium text-ink">{t(link.label)}</span>
              <span className="block truncate text-xs text-ink-subtle" dir="ltr">
                {link.detail}
              </span>
            </span>
            {link.external ? <span className="sr-only"> ({t("helpCenter.opensInNewTab")})</span> : null}
          </a>
        </li>
      ))}
    </ul>
  );
}
