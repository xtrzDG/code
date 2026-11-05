"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { AnimatedPresenceList } from "@/components/motion";
import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { PushDevice } from "../../_lib/notifications";

/** My other devices in this business (another phone, a laptop), each can be turned off from here. */
export function OtherDevices({ devices, onRemove }: { devices: readonly PushDevice[]; onRemove: (device: PushDevice) => Promise<void> }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  if (devices.length === 0) {
    return null;
  }
  return (
    <div className="mt-6 border-t border-line pt-4">
      <h3 className="text-sm font-medium text-ink">{t("notifications.device.otherDevices")}</h3>
      <AnimatedPresenceList
        items={devices}
        getKey={(device) => device.id}
        className="mt-2 divide-y divide-line"
        itemClassName="flex items-center justify-between gap-3 py-2.5"
        renderItem={(device) => {
          const date = format.date(device.created_at);
          return (
            <>
              <div className="min-w-0">
                <p className="truncate text-sm text-ink">{t("notifications.device.otherDevice", { date })}</p>
                <p className="text-xs text-ink-muted">
                  {device.delivered_at
                    ? t("notifications.device.lastDelivered", { time: format.dateTime(device.delivered_at) })
                    : t("notifications.device.neverDelivered")}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                aria-label={t("notifications.device.removeOtherLabel", { date })}
                onClick={() => void onRemove(device)}
              >
                {t("notifications.device.removeOther")}
              </Button>
            </>
          );
        }}
      />
    </div>
  );
}
