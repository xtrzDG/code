"use client";

/**
 * The links the assistant may send, one row per kind (website, menu, map,
 * booking or payment page…): the kind, the address and a way to remove
 * it. The screen saves the rows as they are typed (lib/profile/links).
 */

import { useRef } from "react";

import type { ApiError } from "@/api/errors";
import { IconPlus, IconTrash } from "@/components/icons";
import { Button, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { freeLinkKinds, type LinkKind, type LinkRow } from "@/lib/profile/links";

import { SaveProblem } from "./SaveProblem";

export function LinksField({
  rows,
  onChange,
  problems,
  error,
}: {
  rows: readonly LinkRow[];
  onChange: (rows: LinkRow[]) => void;
  problems: Readonly<Record<string, MessageKey>>;
  error: ApiError | null;
}) {
  const { t } = useI18n();
  const sequence = useRef(0);
  const list = useRef<HTMLUListElement>(null);
  const free = freeLinkKinds(rows);
  const kindName = (kind: LinkKind) => t(`profileEdit.linkKinds.${kind}`);

  const update = (key: string, patch: Partial<LinkRow>) => onChange(rows.map((row) => (row.key === key ? { ...row, ...patch } : row)));

  const add = () => {
    const kind = free[0];
    if (!kind) {
      return;
    }
    sequence.current += 1;
    onChange([...rows, { key: `new-${sequence.current}`, kind, url: "" }]);
    // The new row's address takes the focus once it is drawn.
    requestAnimationFrame(() => list.current?.querySelector<HTMLInputElement>("li:last-child input")?.focus());
  };

  return (
    <section aria-labelledby="profile-links" className="space-y-4 rounded-2xl border border-line bg-surface/80 p-5 backdrop-blur-sm sm:p-6">
      <div className="space-y-1">
        <h2 id="profile-links" className="text-base font-semibold text-ink">
          {t("profileEdit.business.linksTitle")}
        </h2>
        <p className="text-sm text-ink-muted">{t("profileEdit.business.linksHint")}</p>
      </div>
      {rows.length > 0 ? (
        <ul ref={list} className="space-y-3">
          {rows.map((row) => {
            const problem = problems[row.key];
            return (
              <li key={row.key} className="space-y-1">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <Select
                    aria-label={t("profileEdit.business.linkKind")}
                    value={row.kind}
                    onChange={(event) => update(row.key, { kind: event.target.value as LinkKind })}
                    className="sm:w-52"
                  >
                    {[row.kind, ...free].map((kind) => (
                      <option key={kind} value={kind}>
                        {kindName(kind)}
                      </option>
                    ))}
                  </Select>
                  <div className="flex min-w-0 flex-1 items-center gap-2">
                    <Input
                      type="url"
                      inputMode="url"
                      dir="ltr"
                      aria-label={t("profileEdit.business.linkUrl", { kind: kindName(row.kind) })}
                      aria-invalid={problem ? true : undefined}
                      placeholder="https://"
                      maxLength={2048}
                      value={row.url}
                      onChange={(event) => update(row.key, { url: event.target.value })}
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={t("profileEdit.business.removeLink", { kind: kindName(row.kind) })}
                      title={t("profileEdit.business.removeLink", { kind: kindName(row.kind) })}
                      onClick={() => onChange(rows.filter((item) => item.key !== row.key))}
                    >
                      <IconTrash className="size-4" aria-hidden />
                    </Button>
                  </div>
                </div>
                {problem ? <p className="text-sm text-danger">{t(problem)}</p> : null}
              </li>
            );
          })}
        </ul>
      ) : null}
      <SaveProblem error={error} />
      {free.length > 0 ? (
        <Button variant="secondary" size="sm" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={add}>
          {t("profileEdit.business.addLink")}
        </Button>
      ) : null}
    </section>
  );
}
