"use client";

import { Card, ErrorState, LoadingRegion, PageHeader, SkeletonCard } from "@/components/ui";
import { Facts } from "@/components/workspace/Facts";
import { LiveStatus } from "@/components/shell/LiveStatus";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import { useEncryptionKeys } from "../../_lib/useEncryptionKeys";
import { RotationCard } from "./RotationCard";

/**
 * /admin/security: how many keys seal the stored channel and calendar
 * tokens, and moving every token to the newest key (the runbook's
 * "Key rotation", docs/operations/backup-restore.md).
 */
export function EncryptionKeysScreen() {
  const { t } = useI18n();
  const { keys, latest, isRunning, begin, isStarting, startError } = useEncryptionKeys();
  const data = keys.data;

  return (
    <>
      <PageHeader
        title={t("adminSecurity.title")}
        description={t("adminSecurity.description")}
        actions={<LiveStatus updatedAt={keys.updatedAt} isFetching={keys.isFetching && data !== undefined} />}
      />

      {keys.error && !data ? (
        <Card>
          <ErrorState error={keys.error} onRetry={keys.reload} />
        </Card>
      ) : !data ? (
        <EncryptionKeysSkeleton />
      ) : (
        <div className="space-y-6">
          <KeyRingCard keyCount={data.key_count} />
          <RotationCard
            latest={latest}
            keyCount={data.key_count}
            isRunning={isRunning}
            isStarting={isStarting}
            startError={startError}
            onStart={begin}
          />
        </div>
      )}
    </>
  );
}

/** The two cards while the key ring loads (also the route's loading.tsx). */
export function EncryptionKeysSkeleton() {
  const { t } = useI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <div className="space-y-6">
        <SkeletonCard lines={2} />
        <SkeletonCard lines={4} />
      </div>
    </LoadingRegion>
  );
}

function KeyRingCard({ keyCount }: { keyCount: number }) {
  const { t, tp, locale } = useI18n();
  const olderKeys = keyCount - 1;
  return (
    <Card aria-label={t("adminSecurity.ring.title")} title={t("adminSecurity.ring.title")}>
      <div className="space-y-3">
        <Facts items={[{ label: t("adminSecurity.ring.keyCount"), value: formatNumber(keyCount, locale) }]} />
        <p className="text-sm text-ink-muted">
          {olderKeys > 0 ? tp("adminSecurity.ring.several", olderKeys) : t("adminSecurity.ring.single")}
        </p>
      </div>
    </Card>
  );
}
