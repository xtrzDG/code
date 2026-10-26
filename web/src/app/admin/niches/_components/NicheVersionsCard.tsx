"use client";

/**
 * A niche's published versions, newest first, ending with version 0, the
 * code template. Restoring an older one (or the code template) publishes
 * its texts again as the next version, after a confirmation.
 */

import { useState } from "react";

import type { Query } from "@/api/useQuery";
import { useViewerFormat } from "@/components/time/ViewerTimeZone";
import { Badge, Button, Card, ConfirmDialog, ErrorState, SkeletonText, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { NicheTextRelease } from "../_lib/nicheTexts";
import type { useNicheEditor } from "../_lib/useNicheTexts";

type NicheEditing = ReturnType<typeof useNicheEditor>;
type VersionList = NonNullable<NicheEditing["versions"]["data"]>;

export function NicheVersionsCard({ niche, nicheName }: { niche: NicheEditing; nicheName: string }) {
  const { t } = useI18n();
  const toast = useToast();
  const [restoring, setRestoring] = useState<number | null>(null);
  const versions: Query<VersionList> = niche.versions;
  const items = versions.data?.items ?? [];
  const current = items[0]?.version ?? 0;

  const onRestore = async () => {
    if (restoring === null) {
      return;
    }
    const release = await niche.restore(restoring);
    if (release) {
      setRestoring(null);
      toast.success(t("adminNiches.history.restored", { version: release.version }));
    }
  };

  return (
    <Card
      aria-label={t("adminNiches.history.title")}
      title={t("adminNiches.history.title")}
      description={t("adminNiches.history.description")}
    >
      {versions.error && !versions.data ? (
        <ErrorState error={versions.error} onRetry={versions.reload} />
      ) : !versions.data ? (
        <SkeletonText lines={3} />
      ) : (
        <ul className="divide-y divide-line" aria-label={t("adminNiches.history.title")}>
          {items.map((item) => (
            <VersionRow
              key={item.version}
              item={item}
              isCurrent={item.version === current}
              onRestore={() => setRestoring(item.version)}
            />
          ))}
          <li className="flex flex-wrap items-center justify-between gap-2 py-3">
            <div className="space-y-0.5">
              <p className="text-sm font-medium text-ink">{t("adminNiches.history.codeVersion")}</p>
              {items.length === 0 ? <p className="text-xs text-ink-muted">{t("adminNiches.history.empty")}</p> : null}
            </div>
            {current === 0 ? (
              <Badge tone="success">{t("adminNiches.history.inForce")}</Badge>
            ) : (
              <Button size="sm" variant="secondary" onClick={() => setRestoring(0)}>
                {t("adminNiches.history.reset")}
              </Button>
            )}
          </li>
        </ul>
      )}
      <ConfirmDialog
        open={restoring !== null}
        onClose={() => setRestoring(null)}
        onConfirm={onRestore}
        tone="primary"
        isPending={niche.restoring.isPending}
        error={niche.restoring.error}
        title={
          restoring === 0
            ? t("adminNiches.history.resetTitle", { niche: nicheName })
            : t("adminNiches.history.restoreTitle", { niche: nicheName, version: restoring ?? 0 })
        }
        description={t("adminNiches.history.restoreDescription")}
        confirmLabel={restoring === 0 ? t("adminNiches.history.reset") : t("adminNiches.history.restore")}
      />
    </Card>
  );
}

function VersionRow({ item, isCurrent, onRestore }: { item: NicheTextRelease; isCurrent: boolean; onRestore: () => void }) {
  const { t, tp } = useI18n();
  const format = useViewerFormat();
  const when = format.dateTime(item.published_at);
  const kind =
    item.kind === "revert"
      ? t("adminNiches.history.kinds.revert", { version: item.restored_version ?? 0 })
      : t(`adminNiches.history.kinds.${item.kind}`);
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 py-3">
      <div className="min-w-0 space-y-0.5">
        <p className="text-sm font-medium text-ink">
          {t("adminNiches.version", { version: item.version })} · {kind}
        </p>
        <p className="text-xs text-ink-muted">
          {item.published_by_name ? t("adminNiches.history.by", { when, name: item.published_by_name }) : when} ·{" "}
          {tp("adminNiches.history.reworded", item.override_count)}
        </p>
      </div>
      {isCurrent ? (
        <Badge tone="success">{t("adminNiches.history.inForce")}</Badge>
      ) : (
        <Button size="sm" variant="secondary" aria-label={t("adminNiches.history.restoreLabel", { version: item.version })} onClick={onRestore}>
          {t("adminNiches.history.restore")}
        </Button>
      )}
    </li>
  );
}
