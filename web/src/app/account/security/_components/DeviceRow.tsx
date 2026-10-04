"use client";

/** One signed-in device: what it is, when and where it was used, and "Sign out". */

import type { UserSessionView } from "@/api/types";
import { IconMonitor, IconPhone } from "@/components/icons";
import { Badge, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { formatDateTime } from "@/lib/format";

const KIND_LABELS = {
  desktop: "devices.kind.desktop",
  phone: "devices.kind.phone",
  tablet: "devices.kind.tablet",
  unknown: "devices.kind.unknown",
} as const satisfies Record<NonNullable<UserSessionView["device"]["kind"]>, MessageKey>;

export function useDeviceName() {
  const { t } = useI18n();
  return (session: UserSessionView): string => {
    const { browser, operating_system: system, kind } = session.device;
    if (browser && system) {
      return t("devices.on", { browser, system });
    }
    return browser ?? system ?? t(KIND_LABELS[kind ?? "unknown"]);
  };
}

export function DeviceRow({
  session,
  onEnd,
}: {
  session: UserSessionView;
  onEnd: (session: UserSessionView) => void;
}) {
  const { t, locale } = useI18n();
  const deviceName = useDeviceName();
  const name = deviceName(session);
  const when = (value: number) => formatDateTime(value, { locale });
  const isPhone = session.device.kind === "phone" || session.device.kind === "tablet";
  const Icon = isPhone ? IconPhone : IconMonitor;
  const lastUsed = [
    t("devices.lastUsed", { date: when(session.last_seen_at) }),
    session.last_seen_ip ? t("devices.from", { address: session.last_seen_ip }) : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <li className="flex flex-wrap items-start gap-3 py-4 first:pt-0 last:pb-0">
      <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-full bg-surface-muted text-ink-muted">
        <Icon className="size-4" aria-hidden />
      </span>
      <div className="min-w-0 flex-1 space-y-1">
        <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
          <span className="break-words">{name}</span>
          {session.is_current ? <Badge tone="success">{t("devices.thisDevice")}</Badge> : null}
        </p>
        <p className="text-sm text-ink-muted">{lastUsed}</p>
        <p className="text-xs text-ink-subtle">
          {[
            t("devices.signedIn", { date: when(session.created_at) }),
            session.auth_level === "two_factor" ? t("devices.twoFactor") : t("devices.oneFactor"),
            session.idle_expires_at
              ? t("devices.ends", { date: when(Math.min(session.idle_expires_at, session.expires_at)) })
              : null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>
      {session.is_current ? null : (
        <Button variant="secondary" size="sm" aria-label={t("devices.endLabel", { device: name })} onClick={() => onEnd(session)}>
          {t("devices.end")}
        </Button>
      )}
    </li>
  );
}
