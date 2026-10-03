"use client";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCheckCircle, IconSend } from "@/components/icons";
import { MagneticButton } from "@/components/motion";
import { Alert, Badge, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { PushDevice } from "../../_lib/notifications";
import { DEVICE_PROBLEMS, type useMyNotifications } from "../../_lib/useMyNotifications";
import { DeviceVisual } from "./DeviceVisual";
import { OtherDevices } from "./OtherDevices";

type MyNotifications = ReturnType<typeof useMyNotifications>;

/** When this device last got a notification, or why the last one did not arrive. */
function DeviceDelivery({ device }: { device: PushDevice }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  if (device.last_error) {
    return <p className="text-sm text-danger">{t("notifications.device.lastError", { error: device.last_error })}</p>;
  }
  return (
    <p className="text-sm text-ink-muted">
      {device.delivered_at
        ? t("notifications.device.lastDelivered", { time: format.dateTime(device.delivered_at) })
        : t("notifications.device.neverDelivered")}
    </p>
  );
}

/**
 * "On this device": turn this browser's notifications on (the browser asks
 * for permission, then subscribes), send it a test, or turn it off; my
 * other devices below. Explains what stops it: a browser without push, a
 * blocked site, a server without VAPID keys.
 */
export function ThisDeviceCard({ mine }: { mine: MyNotifications }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const { support, problem, publicKey, thisDevice, isSwitching } = mine;
  const isOn = thisDevice !== null;
  const isReady = support === "supported" && publicKey !== null;

  return (
    <section
      aria-labelledby="this-device-title"
      className="relative isolate overflow-hidden rounded-3xl border border-line bg-surface p-5 sm:p-7"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -top-24 -right-16 -z-10 size-72 rounded-full opacity-60 blur-3xl"
        style={{ background: "radial-gradient(circle, color-mix(in oklab, var(--accent-solid) 26%, transparent), transparent 70%)" }}
      />
      <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
        <DeviceVisual isOn={isOn} title={business.name} />
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h2 id="this-device-title" className="text-lg font-semibold tracking-tight text-ink">
              {t("notifications.device.title")}
            </h2>
            <Badge tone={isOn ? "success" : "neutral"} icon={isOn ? <IconCheckCircle className="size-3.5" aria-hidden /> : undefined}>
              {isOn ? t("notifications.device.on") : t("notifications.device.off")}
            </Badge>
          </div>
          <p className="max-w-xl text-sm text-ink-muted">{t("notifications.device.description")}</p>
          {thisDevice ? <DeviceDelivery device={thisDevice} /> : null}

          {support === "unsupported" ? <Alert tone="info">{t("notifications.device.unsupported")}</Alert> : null}
          {support === "denied" ? <Alert tone="warning">{t("notifications.device.denied")}</Alert> : null}
          {support === "supported" && mine.settings.data && publicKey === null ? (
            <Alert tone="info">{t("notifications.device.notConfigured")}</Alert>
          ) : null}
          {problem && problem !== "denied" ? <Alert tone="warning">{t(DEVICE_PROBLEMS[problem])}</Alert> : null}

          <div className="flex flex-wrap items-center gap-2 pt-1">
            {isOn ? (
              <>
                <Button
                  variant="secondary"
                  leadingIcon={<IconSend className="size-4" aria-hidden />}
                  isLoading={mine.isChecking}
                  onClick={() => void mine.sendTest(thisDevice)}
                >
                  {t("notifications.device.test")}
                </Button>
                <Button variant="ghost" isLoading={isSwitching} onClick={() => void mine.disable()}>
                  {t("notifications.device.disable")}
                </Button>
              </>
            ) : (
              <MagneticButton>
                <Button
                  disabled={!isReady}
                  isLoading={isSwitching}
                  className="shadow-[0_14px_32px_-16px_var(--accent-solid)]"
                  onClick={() => void mine.enable()}
                >
                  {t("notifications.device.enable")}
                </Button>
              </MagneticButton>
            )}
          </div>
        </div>
      </div>
      <OtherDevices devices={mine.otherDevices} onRemove={mine.removeOther} />
    </section>
  );
}
