"use client";

import { useEffect, useState } from "react";

import { api } from "@/api/client";
import type { ApiError, ErrorMessageOverrides } from "@/api/errors";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { Alert, Button, Card, ErrorState, LoadingBlock, PageHeader, useToast } from "@/components/ui";
import { ConfirmDialog } from "@/components/workspace/ConfirmDialog";
import { IconRefresh } from "@/components/workspace/icons";
import { OwnerOnlyNote } from "@/components/workspace/OwnerOnly";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { CallForwardingCard } from "./_components/CallForwardingCard";
import { ChannelCard } from "./_components/ChannelCard";
import { CHANNEL_NAMES } from "./_components/channelMeta";
import { ConnectChannelModal } from "./_components/ConnectChannelModal";
import { GoogleCalendarCard } from "./_components/GoogleCalendarCard";
import { StaffTelegramCard } from "./_components/StaffTelegramCard";
import { WebChatSection } from "./_components/WebChatSection";
import {
  CONNECTABLE_CHANNELS,
  channelPathName,
  findChannel,
  isChannelInPlan,
  isChannelOn,
  upsertChannel,
  withoutCalendarReturn,
  type CalendarFailureReason,
  type CalendarReturn,
  type ConnectChannelBody,
  type ConnectableChannel,
} from "./_lib/channels";

const CALENDAR_RETURN_REASONS: Record<CalendarFailureReason, MessageKey> = {
  access_denied: "channels.calendar.returnReasons.access_denied",
  link_expired: "channels.calendar.returnReasons.link_expired",
  no_offline_access: "channels.calendar.returnReasons.no_offline_access",
  provider_error: "channels.calendar.returnReasons.provider_error",
  unknown: "channels.calendar.returnReasons.unknown",
};

const CONNECT_ERRORS: ErrorMessageOverrides = {
  conflict: "channels.errors.accountTaken",
  external_service_error: "channels.errors.provider",
};

/**
 * /channels: customer channels, the website chat's look and code, call
 * forwarding, calendar and staff notifications. `calendarReturn` is what
 * Google's consent page sent back (shown once, then removed from the URL).
 */
export function ChannelsScreen({ calendarReturn: initialCalendarReturn }: { calendarReturn: CalendarReturn | null }) {
  const { t, locale } = useI18n();
  const [calendarReturn, setCalendarReturn] = useState(initialCalendarReturn);
  useEffect(() => {
    if (initialCalendarReturn === null) {
      return;
    }
    // A reload or a shared link must not show the notice again. A null state
    // keeps Next's router in sync with the new address.
    const query = withoutCalendarReturn(window.location.search);
    window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
  }, [initialCalendarReturn]);
  const toast = useToast();
  const { business, isOwner } = useBusiness();
  const [connecting, setConnecting] = useState<ConnectableChannel | null>(null);
  const [disconnecting, setDisconnecting] = useState<ConnectableChannel | null>(null);
  // Failures inside dialogs are shown in them (toasts sit under an open dialog).
  const [connectError, setConnectError] = useState<ApiError | null>(null);
  const [disconnectError, setDisconnectError] = useState<ApiError | null>(null);

  const channels = useApiQuery(
    () => api.GET("/v1/businesses/{business_id}/channels", { params: { path: { business_id: business.id } } }),
    [business.id],
  );
  // Only to mark channels the plan does not include; the page works without it.
  const plans = useApiQuery(
    () => api.GET("/v1/catalog/plans", { params: { query: { country_code: business.country_code, language: locale } } }),
    [business.country_code, locale],
  );
  const planChannels = plans.data?.quotes.find((quote) => quote.plan_key === business.plan_key)?.channels;

  const connect = useApiMutation(
    (kind: ConnectableChannel, body: ConnectChannelBody) =>
      api.PUT("/v1/businesses/{business_id}/channels/{channel}", {
        params: { path: { business_id: business.id, channel: channelPathName(kind) } },
        body,
      }),
    { errorToast: false },
  );
  const disconnect = useApiMutation(
    (kind: ConnectableChannel) =>
      api.DELETE("/v1/businesses/{business_id}/channels/{channel}", {
        params: { path: { business_id: business.id, channel: channelPathName(kind) } },
      }),
    { errorToast: false },
  );

  const runConnect = async (kind: ConnectableChannel, body: ConnectChannelBody): Promise<boolean> => {
    setConnectError(null);
    const result = await connect.run(kind, body);
    if (!result.ok) {
      if (connecting === null) {
        toast.error(result.error, CONNECT_ERRORS);
      } else {
        setConnectError(result.error);
      }
      return false;
    }
    channels.setData((current) => upsertChannel(current, result.data));
    toast.success(t("channels.connectedToast", { channel: t(CHANNEL_NAMES[kind]) }));
    setConnecting(null);
    return true;
  };

  const onConnect = (kind: ConnectableChannel) => {
    if (kind === "web_chat" && !isChannelOn(findChannel(channels.data, kind))) {
      void runConnect(kind, {});
      return;
    }
    setConnectError(null);
    setConnecting(kind);
  };

  const askDisconnect = (kind: ConnectableChannel) => {
    setDisconnectError(null);
    setDisconnecting(kind);
  };

  const onDisconnect = async () => {
    if (!disconnecting) {
      return;
    }
    const kind = disconnecting;
    const result = await disconnect.run(kind);
    if (result.ok) {
      channels.setData((current) => upsertChannel(current, result.data));
      toast.success(t("channels.disconnectedToast", { channel: t(CHANNEL_NAMES[kind]) }));
      setDisconnecting(null);
    } else {
      setDisconnectError(result.error);
    }
  };

  const list = channels.data;
  const hasAnyChannel = CONNECTABLE_CHANNELS.some((kind) => isChannelOn(findChannel(list, kind)));
  const webChat = findChannel(list, "web_chat");
  const isWebChatOn = isChannelOn(webChat);
  const isPhoneOn = isChannelOn(findChannel(list, "phone"));

  return (
    <>
      <PageHeader
        title={t("nav.channels")}
        description={t("pages.channels.description")}
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={channels.reload}
            disabled={channels.isLoading}
            leadingIcon={<IconRefresh className="size-4" aria-hidden />}
          >
            {t("workspace.refresh")}
          </Button>
        }
      />

      {!isOwner ? <OwnerOnlyNote className="mb-6" /> : null}

      {calendarReturn ? (
        <div role={calendarReturn.kind === "connected" ? "status" : undefined} className="mb-6">
          <Alert
            tone={calendarReturn.kind === "connected" ? "success" : "danger"}
            title={calendarReturn.kind === "connected" ? t("channels.calendar.title") : t("channels.calendar.returnErrorTitle")}
          >
            <p>
              {calendarReturn.kind === "connected"
                ? t("channels.calendar.returnConnected")
                : t(CALENDAR_RETURN_REASONS[calendarReturn.reason])}
            </p>
            <Button variant="ghost" size="sm" className="mt-2 -ml-2" onClick={() => setCalendarReturn(null)}>
              {t("channels.calendar.dismiss")}
            </Button>
          </Alert>
        </div>
      ) : null}

      {channels.error && !list ? (
        <Card>
          <ErrorState error={channels.error} onRetry={channels.reload} />
        </Card>
      ) : !list ? (
        <Card>
          <LoadingBlock label={t("common.loading")} />
        </Card>
      ) : (
        <div className="space-y-8">
          <section aria-labelledby="channels-customer" className="space-y-4">
            <div className="space-y-1">
              <h2 id="channels-customer" className="text-lg font-semibold text-ink">
                {t("channels.sectionCustomer")}
              </h2>
              <p className="text-sm text-ink-muted">{t("channels.sectionCustomerHint")}</p>
            </div>
            {!hasAnyChannel ? (
              <Alert tone="info" title={t("channels.emptyTitle")}>
                {t("channels.emptyDescription")}
              </Alert>
            ) : null}
            <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
              {CONNECTABLE_CHANNELS.map((kind) => (
                <ChannelCard
                  key={kind}
                  kind={kind}
                  channel={findChannel(list, kind)}
                  isInPlan={isChannelInPlan(planChannels, kind)}
                  canManage={isOwner}
                  isBusy={(connect.isPending && kind === "web_chat" && connecting === null) || (disconnect.isPending && disconnecting === kind)}
                  onConnect={onConnect}
                  onDisconnect={askDisconnect}
                />
              ))}
            </div>
          </section>

          {isWebChatOn && webChat ? (
            <WebChatSection
              channel={webChat}
              canManage={isOwner}
              onSaved={(updated) => channels.setData((current) => upsertChannel(current, updated))}
            />
          ) : null}
          {isPhoneOn ? <CallForwardingCard /> : null}

          <section aria-labelledby="channels-tools" className="space-y-4">
            <h2 id="channels-tools" className="text-lg font-semibold text-ink">
              {t("channels.sectionTools")}
            </h2>
            <div className="grid gap-4 xl:grid-cols-2">
              <GoogleCalendarCard canManage={isOwner} />
              <StaffTelegramCard canManage={isOwner} />
            </div>
          </section>
        </div>
      )}

      <ConnectChannelModal
        kind={connecting}
        isReconnect={connecting !== null && isChannelOn(findChannel(list, connecting))}
        isPending={connect.isPending}
        error={connectError}
        errorOverrides={CONNECT_ERRORS}
        onClose={() => setConnecting(null)}
        onSubmit={runConnect}
      />

      <ConfirmDialog
        open={disconnecting !== null}
        onClose={() => setDisconnecting(null)}
        onConfirm={onDisconnect}
        isPending={disconnect.isPending}
        error={disconnectError}
        title={disconnecting ? t("channels.disconnectTitle", { channel: t(CHANNEL_NAMES[disconnecting]) }) : ""}
        confirmLabel={t("channels.disconnect")}
      >
        {disconnecting ? (
          <>
            <p>{t("channels.disconnectDescription", { channel: t(CHANNEL_NAMES[disconnecting]) })}</p>
            {disconnecting === "phone" ? <p>{t("channels.disconnectPhoneNote")}</p> : null}
          </>
        ) : null}
      </ConfirmDialog>
    </>
  );
}
