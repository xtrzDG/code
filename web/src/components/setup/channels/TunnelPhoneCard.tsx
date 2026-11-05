"use client";

/**
 * The phone in the "Where do your customers write?" step: a number for
 * calls taken from us in a minute (or asked of our team where the country
 * wants the business's documents), answered by the assistant once it is
 * live. A business already connected with its own number just sees it on.
 */

import { isChannelOn } from "@/app/b/[businessId]/assistant/channels/_lib/channels";
import { PhoneNumberPanel } from "@/app/b/[businessId]/assistant/channels/_components/phoneLine/PhoneNumberPanel";
import type { Schema } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconPhone } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

const CARD = "rounded-2xl border bg-surface/85 p-5 backdrop-blur-sm";

export function TunnelPhoneCard({ channel, onChanged }: { channel: Schema<"ChannelView"> | undefined; onChanged: () => void }) {
  const { t } = useI18n();
  const { isOwner } = useBusiness();
  const isOn = isChannelOn(channel);
  return (
    <section aria-labelledby="tunnel-phone" className={cn(CARD, isOn ? "border-accent/50" : "border-line")}>
      <div className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent" aria-hidden>
          <IconPhone className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 id="tunnel-phone" className="text-base font-semibold text-ink">
            {t("phoneNumbers.tunnel.title")}
          </h2>
          <p className="mt-1 text-sm text-ink-muted">{t("phoneNumbers.tunnel.text")}</p>
        </div>
        {isOn ? (
          <span className="text-xs font-medium text-ink-muted">{t("tunnelTeam.channels.on")}</span>
        ) : null}
      </div>
      <PhoneNumberPanel canManage={isOwner} showGetNumber={!isOn} onChanged={onChanged} />
    </section>
  );
}
