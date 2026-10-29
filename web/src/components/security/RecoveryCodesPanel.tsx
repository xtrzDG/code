"use client";

/**
 * Recovery codes, shown once: copy them, download them as a text file,
 * and say they are saved before going on.
 */

import { useState } from "react";

import { IconDownload } from "@/components/icons";
import { CopyButton } from "@/components/workspace/CopyButton";
import { Alert, Button, Checkbox } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { recoveryCodesFile } from "@/lib/security/secondFactor";

const FILE_NAME = "assistant-workshop-recovery-codes.txt";

function download(text: string): void {
  const url = URL.createObjectURL(
    new Blob([text], { type: "text/plain;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = FILE_NAME;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

export function RecoveryCodesPanel({
  codes,
  account,
  onDone,
  doneLabel,
}: {
  codes: readonly string[];
  /** The phone or e-mail the codes belong to (in the file's heading). */
  account: string;
  onDone: () => void;
  doneLabel?: string;
}) {
  const { t } = useI18n();
  const [saved, setSaved] = useState(false);
  const file = recoveryCodesFile(
    t("mfa.recovery.fileHeading", { account }),
    codes,
  );

  return (
    <div className="space-y-4">
      <Alert tone="warning">{t("mfa.recovery.description")}</Alert>
      <ol
        aria-label={t("mfa.recovery.title")}
        className="grid grid-cols-2 gap-2 rounded-xl bg-surface-muted p-4 font-mono text-sm"
      >
        {codes.map((code) => (
          <li key={code} className="text-center text-ink" translate="no">
            {code}
          </li>
        ))}
      </ol>
      <div className="flex flex-wrap gap-2">
        <CopyButton value={codes.join("\n")} label={t("mfa.recovery.copy")} />
        <Button
          variant="secondary"
          size="sm"
          leadingIcon={<IconDownload className="size-4" aria-hidden />}
          onClick={() => download(file)}
        >
          {t("mfa.recovery.download")}
        </Button>
      </div>
      <Checkbox
        label={t("mfa.recovery.saved")}
        checked={saved}
        onChange={(event) => setSaved(event.target.checked)}
      />
      <Button fullWidth disabled={!saved} onClick={onDone}>
        {doneLabel ?? t("mfa.recovery.continue")}
      </Button>
    </div>
  );
}
