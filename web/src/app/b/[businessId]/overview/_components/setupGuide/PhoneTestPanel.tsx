"use client";

/**
 * "Try it from your phone": the QR code of the hosted chat page (and the
 * Telegram bot, when connected), and the guide listening for the owner's
 * message. Opening it tells the API to listen for half an hour; the setup
 * is reloaded every few seconds meanwhile, and the moment the message
 * arrives the panel says so with a small burst.
 */

import { useEffect, useRef } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import type { Schema } from "@/api/types";
import { IconCheck } from "@/components/icons";
import { Burst } from "@/components/motion";
import { QrImage } from "@/components/setup/QrImage";
import { Spinner } from "@/components/ui";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";

import { displayUrl } from "../../../assistant/channels/_lib/share";

type SetupView = Schema<"SetupView">;

export function PhoneTestPanel({
  setup,
  businessId,
  onStart,
}: {
  setup: SetupView;
  businessId: string;
  /** Tells the API the owner is about to write (once per opening). */
  onStart: () => void;
}) {
  const { t } = useI18n();
  const links = useQuery(queryKeys.channels.share(businessId, ""), () =>
    api.GET("/v1/businesses/{business_id}/share-links", { params: { path: { business_id: businessId }, query: {} } }),
  );
  const started = useRef(false);
  useEffect(() => {
    if (!started.current && setup.guide.phone_tested_at == null) {
      started.current = true;
      onStart();
    }
  }, [onStart, setup.guide.phone_tested_at]);

  const url = links.data?.hosted_chat_url ?? null;
  const telegram = setup.phone_test_links?.find((link) => link.channel === "telegram") ?? null;
  const isTested = setup.guide.phone_tested_at != null;

  if (isTested) {
    return (
      <div role="status" className="relative flex items-center gap-3 rounded-xl bg-success-soft p-4 text-sm text-ink">
        <Burst />
        <IconCheck className="size-5 shrink-0 text-success" aria-hidden />
        <p className="font-medium">{t("setupGuide.phone.success")}</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 rounded-xl border border-line bg-surface-muted p-4 sm:grid-cols-[auto_minmax(0,1fr)] sm:items-center">
      {url ? (
        <QrImage value={url} label={t("setupGuide.phone.qrAlt", { link: displayUrl(url) })} className="mx-auto size-40 sm:mx-0" />
      ) : null}
      <div className="min-w-0 space-y-3">
        <p className="text-sm text-ink">{t("setupGuide.phone.description")}</p>
        {url ? (
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              dir="ltr"
              className="min-w-0 truncate font-mono text-xs text-accent underline-offset-2 hover:underline"
            >
              {displayUrl(url)}
            </a>
            <CopyButton value={url} label={t("setupGuide.phone.copyLink")} />
          </div>
        ) : links.data ? (
          <p className="text-sm text-ink-muted">{t("setupGuide.phone.unavailable")}</p>
        ) : null}
        {telegram ? (
          <p className="text-sm text-ink-muted">
            {t("setupGuide.phone.orTelegram")}{" "}
            <a href={telegram.url} target="_blank" rel="noreferrer" dir="ltr" className="text-accent underline-offset-2 hover:underline">
              {displayUrl(telegram.url)}
            </a>
          </p>
        ) : null}
        <p role="status" className="flex items-center gap-2 text-sm text-ink-muted">
          {setup.guide.is_phone_check_listening ? (
            <>
              <Spinner size="sm" />
              {t("setupGuide.phone.listening")}
            </>
          ) : (
            t("setupGuide.phone.hint")
          )}
        </p>
      </div>
    </div>
  );
}
