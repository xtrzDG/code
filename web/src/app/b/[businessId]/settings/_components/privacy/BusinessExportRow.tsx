"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconDownload } from "@/components/icons";
import { Badge, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  archiveSize,
  canDownload,
  EXPORT_STATUS_TONES,
  isUsedUp,
  MAX_EXPORT_DOWNLOADS,
  shownStatus,
  type BusinessExport,
} from "../../_lib/businessExports";

interface BusinessExportRowProps {
  item: BusinessExport;
  nowUs: number;
  onDownload: (item: BusinessExport) => void;
  /** The export whose link is being made, if any: one download at a time. */
  downloading: string | null;
}

/**
 * One full export: when it was asked, its state, size and records, how
 * long it is kept and how many downloads are left; a ready one downloads
 * through a fresh one-time link.
 */
export function BusinessExportRow({ item, nowUs, onDownload, downloading }: BusinessExportRowProps) {
  const { t, tp } = useI18n();
  const format = useBusinessFormat();
  const status = shownStatus(item, nowUs);
  const downloadable = canDownload(item, nowUs);
  const requested = format.dateTime(item.requested_at);
  const size = item.archive_bytes ? archiveSize(item.archive_bytes) : null;
  const details = [
    size
      ? t(size.unit === "kb" ? "dataExports.full.sizeKb" : "dataExports.full.sizeMb", { size: format.number(size.value) })
      : null,
    item.record_count !== null && item.record_count !== undefined ? tp("dataExports.full.records", item.record_count) : null,
    downloadable && item.expires_at ? t("dataExports.full.readyUntil", { date: format.dateTime(item.expires_at) }) : null,
    downloadable
      ? tp("dataExports.full.downloadsLeft", item.downloads_left, { total: format.number(MAX_EXPORT_DOWNLOADS) })
      : null,
  ].filter((detail): detail is string => detail !== null);

  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
      <div className="min-w-0 flex-1 basis-56">
        <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
          <span>{t("dataExports.full.requested", { date: requested })}</span>
          <Badge tone={EXPORT_STATUS_TONES[status]}>{t(`dataExports.full.status.${status}`)}</Badge>
        </p>
        {details.length > 0 ? <p className="mt-0.5 text-xs text-ink-muted">{details.join(" · ")}</p> : null}
        {status === "failed" ? <p className="mt-1 text-xs text-danger">{t("dataExports.full.failed")}</p> : null}
        {isUsedUp(item, nowUs) ? <p className="mt-1 text-xs text-ink-muted">{t("dataExports.full.usedUp")}</p> : null}
      </div>
      {downloadable ? (
        <Button
          variant="secondary"
          size="sm"
          isLoading={downloading === item.id}
          disabled={downloading !== null && downloading !== item.id}
          leadingIcon={<IconDownload className="size-4" aria-hidden />}
          aria-label={t("dataExports.full.downloadLabel", { date: requested })}
          onClick={() => onDownload(item)}
        >
          {t("dataExports.full.download")}
        </Button>
      ) : null}
    </li>
  );
}
