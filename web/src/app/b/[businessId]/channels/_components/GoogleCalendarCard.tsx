"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCalendar, IconExternal } from "@/components/icons";
import { Alert, Badge, Button, Card, ErrorState, LoadingBlock, useToast } from "@/components/ui";
import { ConfirmDialog } from "@/components/workspace/ConfirmDialog";
import { Facts } from "@/components/workspace/Facts";
import { DANGER_GHOST } from "@/components/workspace/styles";
import { useI18n } from "@/i18n/client";

/**
 * Google Calendar: whether it is connected, which calendar, how syncing
 * goes, and connect (redirect to Google) / disconnect for the owner. After
 * Google's consent page the API sends the owner back to this page, which
 * shows the outcome above the sections.
 */
export function GoogleCalendarCard({ canManage }: { canManage: boolean }) {
  const { t } = useI18n();
  const toast = useToast();
  const format = useBusinessFormat();
  const { business } = useBusiness();
  const [isRedirecting, setRedirecting] = useState(false);
  const [isConfirming, setConfirming] = useState(false);
  const [disconnectError, setDisconnectError] = useState<unknown>(null);

  const status = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/integrations/google-calendar", {
        params: { path: { business_id: business.id } },
      }),
    [business.id],
  );
  const connectUrl = useApiMutation(() =>
    api.GET("/v1/businesses/{business_id}/integrations/google-calendar/connect-url", {
      params: { path: { business_id: business.id } },
    }),
  );
  const disconnect = useApiMutation(
    () =>
      api.DELETE("/v1/businesses/{business_id}/integrations/google-calendar", {
        params: { path: { business_id: business.id } },
      }),
    { errorToast: false },
  );

  const onConnect = async () => {
    const result = await connectUrl.run();
    if (result.ok) {
      setRedirecting(true);
      window.location.assign(result.data.authorization_url);
    }
  };

  const onDisconnect = async () => {
    const result = await disconnect.run();
    if (result.ok) {
      setConfirming(false);
      status.reload();
      toast.success(result.data.was_connected ? t("channels.calendar.disconnectedToast") : t("channels.calendar.notConnectedToast"));
    } else {
      setDisconnectError(result.error);
    }
  };

  const view = status.data;
  const isConnected = view?.is_connected === true;
  const canConnect = view !== undefined && (view.is_configured || isConnected);

  return (
    <Card>
      <div className="flex h-full flex-col gap-4">
        <div className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent" aria-hidden>
            <IconCalendar className="size-5" />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <h3 className="text-base font-semibold text-ink">{t("channels.calendar.title")}</h3>
              {view ? (
                <Badge tone={isConnected ? "success" : "neutral"}>
                  {isConnected ? t("channels.calendar.connected") : t("channels.calendar.notConnected")}
                </Badge>
              ) : null}
            </div>
            <p className="mt-1 text-sm text-ink-muted">{t("channels.calendar.description")}</p>
          </div>
        </div>

        {status.error && !view ? (
          <ErrorState error={status.error} onRetry={status.reload} className="py-4" />
        ) : !view ? (
          <LoadingBlock label={t("common.loading")} className="min-h-20" />
        ) : (
          <>
            {isConnected ? (
              <Facts
                items={[
                  {
                    label: t("channels.calendar.calendarLabel"),
                    value: (
                      <span dir="auto">
                        {view.calendar_name ??
                          (view.calendar_id === "primary" ? t("channels.calendar.primaryCalendar") : view.calendar_id)}
                      </span>
                    ),
                    wide: true,
                  },
                  view.connected_at
                    ? { label: t("channels.calendar.connectedAt"), value: format.dateTime(view.connected_at) }
                    : null,
                  {
                    label: t("channels.calendar.lastSync"),
                    value: view.last_synced_at ? format.dateTime(view.last_synced_at) : t("channels.calendar.neverSynced"),
                  },
                ]}
              />
            ) : null}

            {isConnected && view.last_sync_error ? (
              <Alert tone="warning" title={t("channels.calendar.syncErrorTitle")}>
                <p>
                  {t("channels.calendar.syncErrorDescription", {
                    date: view.last_sync_error_at ? format.dateTime(view.last_sync_error_at) : "—",
                    reason: view.last_sync_error,
                  })}
                </p>
                <p className="mt-1">{t("channels.calendar.syncErrorHint")}</p>
              </Alert>
            ) : null}

            {!view.is_configured && !isConnected ? (
              <Alert tone="info">{t("channels.calendar.notConfigured")}</Alert>
            ) : null}

            {canManage && canConnect ? (
              <>
                {isConnected ? <p className="text-xs text-ink-subtle">{t("channels.calendar.reconnectNote")}</p> : null}
                <div className="mt-auto flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant={isConnected ? "secondary" : "primary"}
                    onClick={onConnect}
                    isLoading={connectUrl.isPending || isRedirecting}
                    loadingText={t("channels.calendar.redirecting")}
                    leadingIcon={<IconExternal className="size-4" aria-hidden />}
                  >
                    {isConnected ? t("channels.calendar.reconnect") : t("channels.calendar.connect")}
                  </Button>
                  {isConnected ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      className={DANGER_GHOST}
                      onClick={() => {
                        setDisconnectError(null);
                        setConfirming(true);
                      }}
                      disabled={isRedirecting}
                    >
                      {t("channels.calendar.disconnect")}
                    </Button>
                  ) : null}
                </div>
              </>
            ) : null}
          </>
        )}
      </div>
      <ConfirmDialog
        open={isConfirming}
        onClose={() => setConfirming(false)}
        onConfirm={onDisconnect}
        isPending={disconnect.isPending}
        error={disconnectError}
        title={t("channels.calendar.disconnectTitle")}
        description={t("channels.calendar.disconnectDescription")}
        confirmLabel={t("channels.calendar.disconnect")}
      />
    </Card>
  );
}
