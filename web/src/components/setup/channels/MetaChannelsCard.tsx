"use client";

/**
 * The setup tunnel's card for Meta's channels. Where the server offers
 * "Continue with Facebook", WhatsApp, Instagram and Messenger connect here
 * with the same dialog as on the Channels page (Facebook first, the manual
 * fields under "Enter details manually"); otherwise the card says they come
 * after launch, as before.
 */

import { useState } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { queryKeys } from "@/api/queryKeys";
import { sectionQueries } from "@/api/sectionQueries";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { CHANNEL_NAMES } from "@/app/b/[businessId]/assistant/channels/_components/channelMeta";
import { ConnectChannelModal } from "@/app/b/[businessId]/assistant/channels/_components/ConnectChannelModal";
import {
  channelPathName,
  findChannel,
  isChannelOn,
  upsertChannel,
  type ConnectableChannel,
} from "@/app/b/[businessId]/assistant/channels/_lib/channels";
import type { ConnectChannelBody } from "@/app/b/[businessId]/assistant/channels/_lib/connectForm";
import { offersFacebook, type MetaChannel } from "@/app/b/[businessId]/assistant/channels/_lib/metaSignIn";
import { useResumeFacebook } from "@/app/b/[businessId]/assistant/channels/_lib/useResumeFacebook";
import { IconFacebook, IconWhatsApp } from "@/components/icons";
import { Badge, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

const CARD = "rounded-2xl border bg-surface/85 p-5 backdrop-blur-sm";
const CHANNELS: readonly MetaChannel[] = ["whatsapp", "instagram", "messenger"];
const CONNECT_ERRORS = { conflict: "channels.errors.accountTaken", external_service_error: "channels.errors.provider" } as const;

export function MetaChannelsCard({ businessId }: { businessId: string }) {
  const { t } = useI18n();
  const channelsQuery = sectionQueries.channels(businessId);
  const channels = useQuery(channelsQuery.key, channelsQuery.fetch);
  const options = useQuery(queryKeys.channels.metaSignIn(businessId), () =>
    api.GET("/v1/businesses/{business_id}/channels/meta/sign-in", { params: { path: { business_id: businessId } } }),
  );
  const offered = CHANNELS.filter((kind) => offersFacebook(options.data, kind));
  const [connecting, setConnecting] = useState<MetaChannel | null>(null);
  const [connectError, setConnectError] = useState<ApiError | null>(null);
  const resumable = (kind: MetaChannel) => (offered.includes(kind) ? kind : null);
  // One hook per channel: the reloaded page names the one to reopen.
  useResumeFacebook(resumable("whatsapp"), true, setConnecting);
  useResumeFacebook(resumable("instagram"), true, setConnecting);
  useResumeFacebook(resumable("messenger"), true, setConnecting);

  const connect = useMutation(
    (kind: ConnectableChannel, body: ConnectChannelBody) =>
      api.PUT("/v1/businesses/{business_id}/channels/{channel}", {
        params: { path: { business_id: businessId, channel: channelPathName(kind) } },
        body,
      }),
    { errorToast: false, stale: [queryKeys.assistant.all(businessId), queryKeys.channels.all(businessId)] },
  );
  const submitManual = async (kind: ConnectableChannel, body: ConnectChannelBody): Promise<boolean> => {
    setConnectError(null);
    const result = await connect.run(kind, body);
    if (!result.ok) {
      setConnectError(result.error);
      return false;
    }
    channels.setData((current) => upsertChannel(current, result.data));
    setConnecting(null);
    return true;
  };

  return (
    <section
      aria-labelledby="tunnel-meta"
      className={cn(CARD, offered.length > 0 ? "border-line" : "border-dashed border-line-strong")}
    >
      <div className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-surface-muted text-ink-muted" aria-hidden>
          {offered.length > 0 ? <IconFacebook className="size-5" /> : <IconWhatsApp className="size-5" />}
        </span>
        <div className="min-w-0 flex-1">
          <h2 id="tunnel-meta" className="text-base font-semibold text-ink">
            {offered.length > 0 ? t("metaConnect.tunnel.title") : t("tunnelTeam.channels.later.title")}
          </h2>
          <p className="mt-1 text-sm text-ink-muted">
            {offered.length > 0 ? t("metaConnect.tunnel.text") : t("tunnelTeam.channels.later.text")}
          </p>
        </div>
        {offered.length === 0 ? <Badge tone="neutral">{t("tunnelTeam.channels.later.badge")}</Badge> : null}
      </div>

      {offered.length > 0 ? (
        <ul className="mt-4 flex flex-wrap gap-2">
          {offered.map((kind) => {
            const name = t(CHANNEL_NAMES[kind]);
            return (
              <li key={kind}>
                {isChannelOn(findChannel(channels.data, kind)) ? (
                  <Badge tone="success">{`${name}: ${t("metaConnect.tunnel.connected")}`}</Badge>
                ) : (
                  <Button size="sm" variant="secondary" onClick={() => setConnecting(kind)}>
                    {t("metaConnect.tunnel.connect", { channel: name })}
                  </Button>
                )}
              </li>
            );
          })}
        </ul>
      ) : null}

      <ConnectChannelModal
        kind={connecting}
        isReconnect={false}
        isPending={connect.isPending}
        error={connectError}
        errorOverrides={CONNECT_ERRORS}
        onClose={() => setConnecting(null)}
        onSubmit={submitManual}
      />
    </section>
  );
}
