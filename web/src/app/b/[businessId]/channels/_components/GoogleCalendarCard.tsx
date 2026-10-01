"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconCalendar, IconExternal } from "@/components/icons";
import { Button, Card, useToast } from "@/components/ui";
import { ConfirmDialog } from "@/components/workspace/ConfirmDialog";
import { DANGER_GHOST } from "@/components/workspace/styles";
import { useI18n } from "@/i18n/client";

/**
 * Google Calendar: the owner is sent to Google's consent page; bookings are
 * then mirrored in the calendar. The API has no "is connected" read, so
 * both actions are offered (connecting again replaces the calendar).
 */
export function GoogleCalendarCard({ canManage }: { canManage: boolean }) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [isRedirecting, setRedirecting] = useState(false);
  const [isConfirming, setConfirming] = useState(false);

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
  const [disconnectError, setDisconnectError] = useState<unknown>(null);

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
      toast.success(result.data.was_connected ? t("channels.calendar.disconnectedToast") : t("channels.calendar.notConnectedToast"));
    } else {
      setDisconnectError(result.error);
    }
  };

  return (
    <Card>
      <div className="flex h-full flex-col gap-4">
        <div className="flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent" aria-hidden>
            <IconCalendar className="size-5" />
          </span>
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-ink">{t("channels.calendar.title")}</h3>
            <p className="mt-1 text-sm text-ink-muted">{t("channels.calendar.description")}</p>
          </div>
        </div>
        {canManage ? (
          <>
            <p className="text-xs text-ink-subtle">{t("channels.calendar.reconnectNote")}</p>
            <div className="mt-auto flex flex-wrap gap-2">
              <Button
                size="sm"
                onClick={onConnect}
                isLoading={connectUrl.isPending || isRedirecting}
                loadingText={t("channels.calendar.redirecting")}
                leadingIcon={<IconExternal className="size-4" aria-hidden />}
              >
                {t("channels.calendar.connect")}
              </Button>
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
            </div>
          </>
        ) : null}
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
