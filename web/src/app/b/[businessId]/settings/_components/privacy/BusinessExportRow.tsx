"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconDownload } from "@/components/icons";
import { Badge, buttonClasses } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  archiveSize,
  downloadHref,
  EXPORT_STATUS_TONES,
  shownStatus,
  type BusinessExport,
} from "../../_lib/businessExports";

/** One full export: when it was asked, its state, size and records, and its signed link while it works. */
export function BusinessExportRow({ item, nowUs }: { item: BusinessExport; nowUs: number }) {
  const { t, tp } = useI18n();
  const format = useBusinessFormat();
  const status = shownStatus(item, nowUs);
  const href = downloadHref(item, nowUs);
  const requested = format.dateTime(item.requested_at);
  const size = item.archive_bytes ? archiveSize(item.archive_bytes) : null;
  const details = [
    size
      ? t(size.unit === "kb" ? "dataExports.full.sizeKb" : "dataExports.full.sizeMb", { size: format.number(size.value) })
      : null,
    item.record_count !== null && item.record_count !== undefined ? tp("dataExports.full.records", item.record_count) : null,
    href && item.expires_at ? t("dataExports.full.readyUntil", { date: format.dateTime(item.expires_at) }) : null,
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
      </div>
      {href ? (
        <a
          href={href}
          download
          aria-label={t("dataExports.full.downloadLabel", { date: requested })}
          className={buttonClasses({ variant: "secondary", size: "sm" })}
        >
          <IconDownload className="size-4" aria-hidden />
          <span>{t("dataExports.full.download")}</span>
        </a>
      ) : null}
    </li>
  );
}
