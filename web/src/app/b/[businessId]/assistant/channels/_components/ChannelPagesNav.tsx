"use client";

/**
 * On a phone, under the channel cards: the longer parts of Channels as
 * pages of their own (the website chat's look and code, call forwarding,
 * sharing), one row each with what is inside.
 */

import Link from "next/link";
import type { ComponentType } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconChevronRight, IconLink, IconPhone, IconWindow, type IconProps } from "@/components/icons";
import { useI18n } from "@/i18n/client";

import { channelSubpagePath, offeredSubpages, type ChannelSubpage } from "../_lib/channelPages";

const ICONS: Record<ChannelSubpage, ComponentType<IconProps>> = {
  website: IconWindow,
  calls: IconPhone,
  share: IconLink,
};

export function ChannelPagesNav({ isWebChatOn, isPhoneOn }: { isWebChatOn: boolean; isPhoneOn: boolean }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  return (
    <nav aria-labelledby="channels-pages" className="space-y-3">
      <h2 id="channels-pages" className="text-lg font-semibold text-ink">
        {t("channelPages.heading")}
      </h2>
      <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface">
        {offeredSubpages({ isWebChatOn, isPhoneOn }).map((page) => {
          const Icon = ICONS[page];
          return (
            <li key={page}>
              <Link
                href={channelSubpagePath(business.id, page)}
                data-channel-page={page}
                className="flex min-h-16 items-center gap-3 px-4 py-3 transition-colors hover:bg-surface-muted active:bg-surface-muted"
              >
                <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent-ink" aria-hidden>
                  <Icon className="size-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-semibold text-ink">{t(`channelPages.${page}.title`)}</span>
                  <span className="block text-xs text-ink-muted">{t(`channelPages.${page}.hint`)}</span>
                </span>
                <IconChevronRight className="size-4 shrink-0 text-ink-subtle rtl:rotate-180" aria-hidden />
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
