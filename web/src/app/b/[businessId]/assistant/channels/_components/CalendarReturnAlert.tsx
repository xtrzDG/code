"use client";

/** What Google's consent page sent back: the calendar is connected, or why it is not (with Dismiss). */

import { Alert, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import type { CalendarFailureReason, CalendarReturn } from "../_lib/calendarReturn";

const CALENDAR_RETURN_REASONS: Record<CalendarFailureReason, MessageKey> = {
  access_denied: "channels.calendar.returnReasons.access_denied",
  link_expired: "channels.calendar.returnReasons.link_expired",
  no_offline_access: "channels.calendar.returnReasons.no_offline_access",
  provider_error: "channels.calendar.returnReasons.provider_error",
  unknown: "channels.calendar.returnReasons.unknown",
};

export function CalendarReturnAlert({ calendarReturn, onDismiss }: { calendarReturn: CalendarReturn; onDismiss: () => void }) {
  const { t } = useI18n();
  const isConnected = calendarReturn.kind === "connected";
  return (
    <div role={isConnected ? "status" : undefined} className="mb-6">
      <Alert
        tone={isConnected ? "success" : "danger"}
        title={isConnected ? t("channels.calendar.title") : t("channels.calendar.returnErrorTitle")}
      >
        <p>
          {calendarReturn.kind === "connected"
            ? t("channels.calendar.returnConnected")
            : t(CALENDAR_RETURN_REASONS[calendarReturn.reason])}
        </p>
        <Button variant="ghost" size="sm" className="mt-2 -ms-2" onClick={onDismiss}>
          {t("channels.calendar.dismiss")}
        </Button>
      </Alert>
    </div>
  );
}
