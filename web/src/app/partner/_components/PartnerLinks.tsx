"use client";

import { useId, useState } from "react";

import type { Schema } from "@/api/types";
import { QrImage } from "@/components/setup/QrImage";
import { Button, Card, Field, Input } from "@/components/ui";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";
import { isSourceTag, linkWithSource } from "@/lib/referrals/referralLinks";

type PartnerCodeView = Schema<"PartnerCodeView">;

/**
 * The partner's link generator: one link per code, with the place it is
 * shared in as its `src` tag (so their reports say where sign-ups came
 * from), to copy or to show as a QR code.
 */
export function PartnerLinks({ codes }: { codes: readonly PartnerCodeView[] }) {
  const { t } = useI18n();
  const [source, setSource] = useState("");
  const trimmed = source.trim();
  const isInvalid = trimmed !== "" && !isSourceTag(trimmed);

  return (
    <Card title={t("partnerPortal.links.title")} description={t("partnerPortal.links.description")}>
      {codes.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("partnerPortal.links.none")}</p>
      ) : (
        <div className="space-y-4">
          <Field
            label={t("partnerPortal.links.source")}
            hint={t("partnerPortal.links.sourceHint")}
            error={isInvalid ? t("partnerPortal.links.sourceInvalid") : undefined}
          >
            {(control) => (
              <Input
                {...control}
                className="max-w-xs"
                value={source}
                placeholder={t("partnerPortal.links.sourcePlaceholder")}
                autoComplete="off"
                spellCheck={false}
                onChange={(event) => setSource(event.target.value)}
              />
            )}
          </Field>
          <ul className="space-y-3">
            {codes.map((code) => (
              <CodeLink key={code.code} code={code} source={isInvalid ? "" : trimmed} />
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

function CodeLink({ code, source }: { code: PartnerCodeView; source: string }) {
  const { t } = useI18n();
  const [showsQr, setShowsQr] = useState(false);
  const qrId = useId();
  const link = code.link ? linkWithSource(code.link, source) : null;

  return (
    <li className="space-y-2 rounded-lg border border-line p-3">
      <p className="text-xs text-ink-subtle">
        {t("partnerPortal.links.code")}: <span className="font-mono text-ink">{code.code}</span>
      </p>
      {link ? (
        <>
          <p className="font-mono text-sm break-all text-ink" data-testid="partner-link">
            {link}
          </p>
          <div className="flex flex-wrap gap-2">
            <CopyButton value={link} />
            <Button variant="ghost" size="sm" aria-expanded={showsQr} aria-controls={qrId} onClick={() => setShowsQr((value) => !value)}>
              {showsQr ? t("partnerPortal.links.hideQr") : t("partnerPortal.links.showQr")}
            </Button>
          </div>
          {showsQr ? (
            <div id={qrId}>
              <QrImage value={link} label={t("partnerPortal.links.qrLabel", { code: code.code })} className="size-40" />
            </div>
          ) : null}
        </>
      ) : null}
    </li>
  );
}
