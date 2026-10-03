"use client";

import { Alert, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { GeneralSettings } from "../../_lib/useGeneralSettings";

/** Why the form changed under the owner: a save refused as stale, and a reload that failed too. */
export function StaleNotices({ settings }: { settings: GeneralSettings }) {
  const { t } = useI18n();
  const { isReloadFailed, isStale, isReloading, loadCurrent, closeStale } = settings;
  return (
    <>
      {isReloadFailed ? (
        <Alert
          tone="danger"
          title={t("settings.general.staleTitle")}
          action={
            <Button variant="secondary" size="sm" isLoading={isReloading} onClick={() => void loadCurrent()}>
              {t("settings.general.staleReload")}
            </Button>
          }
        >
          {t("settings.general.staleReloadFailed")}
        </Alert>
      ) : null}
      {isStale ? (
        <Alert
          tone="warning"
          title={t("settings.general.staleTitle")}
          action={
            <Button variant="secondary" size="sm" onClick={closeStale}>
              {t("common.close")}
            </Button>
          }
        >
          {t("settings.general.staleDescription")}
        </Alert>
      ) : null}
    </>
  );
}
