"use client";

import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";

import { dialHref } from "../_lib/channels";
import type { ForwardingCodeRow } from "../_lib/forwardingCodes";

/**
 * Forwarding codes to dial, one row each: what the code does, the code with
 * its copy button and, on a phone, a link that opens the dialer with it
 * (copying is the sure way: an iPhone does not dial a tel: link with * or #).
 */
export function ForwardingCodeList({ rows }: { rows: readonly ForwardingCodeRow[] }) {
  const { t } = useI18n();
  return (
    <ul className="divide-y divide-line rounded-xl border border-line">
      {rows.map((row) => (
        <li key={row.key} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
          <div className="min-w-0 flex-1 basis-48">
            <p className="text-sm font-medium text-ink">{t(row.label)}</p>
            <p className="text-xs text-ink-muted">{row.description}</p>
          </div>
          <div className="flex items-center gap-1">
            <code dir="ltr" className="rounded-md bg-surface-muted px-2 py-1 font-mono text-sm text-ink">
              {row.dialCode}
            </code>
            <CopyButton value={row.dialCode} iconOnly label={`${t("workspace.copy")} ${row.dialCode}`} />
            <a
              href={dialHref(row.dialCode)}
              className="rounded-lg px-2 py-1 text-sm font-medium text-accent hover:bg-accent-soft focus-visible:outline-2 focus-visible:outline-focus sm:hidden"
              aria-label={t("channels.forwarding.dialLabel", { code: row.dialCode })}
            >
              {t("channels.forwarding.dial")}
            </a>
          </div>
        </li>
      ))}
    </ul>
  );
}
