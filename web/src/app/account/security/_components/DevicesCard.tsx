"use client";

/**
 * Account → Security → "Where you are signed in": every device with a live
 * session, this one first; sign one out, or every other one at once.
 */

import { useState } from "react";

import type { UserSessionView } from "@/api/types";
import { Button, Card, ConfirmDialog, ErrorState, SkeletonCard, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { otherSessionCount } from "@/lib/security/devices";

import { DeviceRow, useDeviceName } from "./DeviceRow";
import { useDevices } from "./useDevices";

export function DevicesCard({ isPlatformAdmin }: { isPlatformAdmin: boolean }) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const deviceName = useDeviceName();
  const devices = useDevices();
  const [ending, setEnding] = useState<UserSessionView | null>(null);
  const [isEndingOthers, setEndingOthers] = useState(false);
  const others = otherSessionCount(devices.items);

  const endOne = async () => {
    if (ending && (await devices.endOne(ending.id))) {
      setEnding(null);
      toast.success(t("devices.ended"));
    }
  };

  const endOthers = async () => {
    const count = await devices.endEverywhereElse();
    if (count !== null) {
      setEndingOthers(false);
      toast.success(tp("devices.endedOthers", count));
    }
  };

  if (devices.sessions.error && !devices.sessions.data) {
    return (
      <Card title={t("devices.title")}>
        <ErrorState error={devices.sessions.error} onRetry={devices.sessions.reload} />
      </Card>
    );
  }
  if (!devices.sessions.data) {
    return <SkeletonCard lines={4} />;
  }

  return (
    <Card
      aria-label={t("devices.title")}
      title={t("devices.title")}
      description={isPlatformAdmin ? t("devices.descriptionAdmin") : t("devices.description")}
      actions={
        others > 0 ? (
          <Button variant="secondary" size="sm" onClick={() => setEndingOthers(true)}>
            {t("devices.endOthers")}
          </Button>
        ) : null
      }
    >
      <ul className="divide-y divide-line">
        {devices.items.map((session) => (
          <DeviceRow key={session.id} session={session} onEnd={setEnding} />
        ))}
      </ul>
      <p className="mt-4 text-sm text-ink-muted">{others > 0 ? t("devices.notYou") : t("devices.onlyThis")}</p>

      <ConfirmDialog
        open={ending !== null}
        onClose={() => setEnding(null)}
        onConfirm={endOne}
        isPending={devices.isEnding}
        error={devices.endError}
        title={t("devices.endTitle")}
        description={ending ? `${deviceName(ending)}. ${t("devices.endDescription")}` : undefined}
        confirmLabel={t("devices.end")}
      />
      <ConfirmDialog
        open={isEndingOthers}
        onClose={() => setEndingOthers(false)}
        onConfirm={endOthers}
        isPending={devices.isEndingOthers}
        error={devices.endOthersError}
        title={t("devices.endOthersTitle")}
        description={t("devices.endOthersDescription")}
        confirmLabel={t("devices.endOthers")}
      />
    </Card>
  );
}
