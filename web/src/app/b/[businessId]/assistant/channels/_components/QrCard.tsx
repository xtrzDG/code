"use client";

import { useMemo } from "react";

import { IconDownload } from "@/components/icons";
import { Button, Card, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { encodeQr, qrPath, qrPngBlob, qrSide, qrSvgDocument, saveBlob } from "../_lib/qrCode";
import { displayUrl, downloadName, LINK_KIND_LABELS, type ShareLink, type ShareSource } from "../_lib/share";
import { TableCardPanel } from "./TableCardPanel";

/**
 * The QR code of the chosen link: on screen, as PNG and SVG files, and on
 * a printable table card. Made in the browser; it changes with the link's
 * tag.
 */
export function QrCard({
  link,
  slug,
  source,
  accent,
  businessName,
  languages,
  defaultLanguage,
}: {
  link: ShareLink & { url: string };
  slug: string;
  source: ShareSource;
  accent: string | null;
  businessName: string;
  languages: readonly string[];
  defaultLanguage: string;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const matrix = useMemo(() => encodeQr(link.url), [link.url]);
  const name = t(LINK_KIND_LABELS[link.kind]);
  const fileName = downloadName(slug, link.kind, source);
  const side = qrSide(matrix);

  const downloadPng = async () => {
    const blob = await qrPngBlob(matrix);
    if (blob) {
      saveBlob(blob, `${fileName}.png`);
    } else {
      toast.info(t("share.printFailed"));
    }
  };
  const downloadSvg = () => {
    saveBlob(new Blob([qrSvgDocument(matrix, displayUrl(link.url))], { type: "image/svg+xml" }), `${fileName}.svg`);
  };

  return (
    <Card title={t("share.qrTitle")} description={name} className="min-w-0">
      <div className="space-y-5">
        <figure className="space-y-3">
          <div className="mx-auto w-full max-w-60 rounded-xl bg-white p-2 shadow-sm ring-1 ring-line">
            <svg
              viewBox={`0 0 ${side} ${side}`}
              role="img"
              aria-label={t("share.qrAlt", { link: displayUrl(link.url) })}
              data-testid="share-qr"
              data-qr-text={link.url}
              shapeRendering="crispEdges"
              className="block h-auto w-full"
            >
              <rect width={side} height={side} fill="#ffffff" />
              <path d={qrPath(matrix)} fill="#000000" />
            </svg>
          </div>
          <figcaption dir="ltr" className="truncate text-center font-mono text-xs text-ink-muted">
            {displayUrl(link.url)}
          </figcaption>
        </figure>
        <div className="flex flex-wrap justify-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            leadingIcon={<IconDownload className="size-4" aria-hidden />}
            aria-label={t("share.downloadLabel", { format: "PNG" })}
            onClick={() => void downloadPng()}
          >
            {t("share.downloadPng")}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            leadingIcon={<IconDownload className="size-4" aria-hidden />}
            aria-label={t("share.downloadLabel", { format: "SVG" })}
            onClick={downloadSvg}
          >
            {t("share.downloadSvg")}
          </Button>
        </div>
        <TableCardPanel
          matrix={matrix}
          linkText={displayUrl(link.url)}
          accent={accent}
          businessName={businessName}
          languages={languages}
          defaultLanguage={defaultLanguage}
        />
      </div>
    </Card>
  );
}
