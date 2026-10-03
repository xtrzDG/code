"use client";

import type { ComponentType } from "react";

import { IconChat, IconInstagram, IconMessenger, IconPhone, IconSend, IconWhatsApp, type IconProps } from "@/components/icons";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { displayUrl, LINK_KIND_LABELS, type ShareLink, type ShareLinkKind } from "../_lib/share";

const LINK_ICONS: Record<ShareLinkKind, ComponentType<IconProps>> = {
  hosted_chat: IconChat,
  telegram: IconSend,
  whatsapp: IconWhatsApp,
  instagram: IconInstagram,
  messenger: IconMessenger,
  phone: IconPhone,
};

/** A link per switched-on channel: copy it, or show its QR code. */
export function ShareLinkList({
  links,
  selected,
  onSelect,
}: {
  links: readonly ShareLink[];
  selected: ShareLinkKind | null;
  onSelect: (kind: ShareLinkKind) => void;
}) {
  const { t } = useI18n();

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-ink">{t("share.linksTitle")}</h3>
      <ul className="divide-y divide-line rounded-xl border border-line">
        {links.map((link) => {
          const Icon = LINK_ICONS[link.kind];
          const name = t(LINK_KIND_LABELS[link.kind]);
          const isSelected = link.url ? selected === link.kind : false;
          return (
            <li key={link.kind} className={cn("flex items-center gap-3 px-3 py-2.5", isSelected && "bg-accent-soft/50")}>
              <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-surface-muted text-ink-muted">
                <Icon className="size-4" aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-ink">{name}</p>
                {link.url ? (
                  <p dir="ltr" className="truncate text-left font-mono text-xs text-ink-muted rtl:text-right">
                    {link.label && link.kind !== "hosted_chat" ? `${link.label} · ` : ""}
                    {displayUrl(link.url)}
                  </p>
                ) : (
                  <p className="text-xs text-warning">
                    {link.gap === "reconnect_channel"
                      ? t("share.gaps.reconnect_channel", { channel: name })
                      : t("share.gaps.not_configured")}
                  </p>
                )}
              </div>
              {link.url ? (
                <div className="flex shrink-0 items-center gap-1">
                  <CopyButton value={link.url} iconOnly label={`${t("workspace.copy")}: ${name}`} />
                  <button
                    type="button"
                    aria-pressed={isSelected}
                    aria-label={t("share.showQr", { link: name })}
                    title={t("share.showQr", { link: name })}
                    onClick={() => onSelect(link.kind)}
                    className={cn(
                      "inline-flex size-8 items-center justify-center rounded-lg text-ink-muted transition-colors",
                      "hover:bg-surface-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
                      isSelected && "bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent",
                    )}
                  >
                    <QrGlyph />
                  </button>
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** A small QR-code glyph for the "show QR code" buttons. */
function QrGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={1.75} aria-hidden focusable="false">
      <rect x="3.5" y="3.5" width="6" height="6" rx="1" />
      <rect x="14.5" y="3.5" width="6" height="6" rx="1" />
      <rect x="3.5" y="14.5" width="6" height="6" rx="1" />
      <path d="M14.5 14.5h2.5v2.5h-2.5zM18 18h2.5v2.5H18zM14.5 20.5h1M20.5 14.5v1" />
    </svg>
  );
}
