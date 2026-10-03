"use client";

import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconExternal, IconPencil } from "@/components/icons";
import { Alert, Button, Field, Input, buttonClasses, useToast } from "@/components/ui";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { splitForMiddleEllipsis } from "@/lib/middleEllipsis";

import { displayUrl, isValidSlug, normalizeSlugInput, SLUG_MAX_LENGTH, type ShareLinks } from "../_lib/share";

const REFUSALS: Record<string, MessageKey> = {
  slug_taken: "share.addressTaken",
  slug_reserved: "share.addressReserved",
};

/** "app.example.com/c/" of the page's address, shown before the editable part. */
function addressPrefix(url: string): string {
  try {
    const parsed = new URL(url);
    return `${parsed.host}/c/`;
  } catch {
    return "/c/";
  }
}

function refusalKey(error: ApiError): MessageKey | null {
  const known = error.reasons.find((reason) => Object.hasOwn(REFUSALS, reason.code));
  if (known) {
    return REFUSALS[known.code] ?? null;
  }
  return error.code === "validation_failed" ? "share.addressInvalid" : null;
}

/** The hosted chat page: its link (copy, open) and, for owners, a new address. */
export function ShareAddress({ view, isWebChatOn, canManage }: { view: ShareLinks; isWebChatOn: boolean; canManage: boolean }) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [draft, setDraft] = useState<string | null>(null);
  const [error, setError] = useState<MessageKey | null>(null);
  const save = useMutation(
    (slug: string) =>
      api.PUT("/v1/businesses/{business_id}/public-slug", {
        params: { path: { business_id: business.id } },
        body: { slug },
      }),
    { errorToast: false, invalidate: [queryKeys.channels.shareAll(business.id)] },
  );

  const url = view.links.find((link) => link.kind === "hosted_chat")?.url ?? null;

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const slug = draft ?? "";
    if (!isValidSlug(slug)) {
      setError("share.addressInvalid");
      return;
    }
    if (slug === view.slug) {
      setDraft(null);
      return;
    }
    const result = await save.run(slug);
    if (result.ok) {
      setDraft(null);
      setError(null);
      toast.success(t("share.addressSaved"));
      return;
    }
    const key = refusalKey(result.error);
    if (key) {
      setError(key);
    } else {
      toast.error(result.error);
    }
  };

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <h3 className="text-sm font-medium text-ink">{t("share.pageLabel")}</h3>
        <p className="text-sm text-ink-muted">{t("share.pageHint")}</p>
      </div>
      {!url ? (
        <Alert tone="info">{t("share.notConfigured")}</Alert>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          {/* A middle ellipsis: the host gives way first, the page's own name stays readable. */}
          <code
            dir="ltr"
            data-testid="share-chat-page-url"
            title={displayUrl(url)}
            className="flex min-w-0 flex-[1_1_12rem] rounded-lg border border-line bg-surface-muted px-3 py-2 font-mono text-sm text-ink"
          >
            <span className="min-w-[4ch] shrink-[1000] truncate">{splitForMiddleEllipsis(displayUrl(url)).head}</span>
            <span className="min-w-0 truncate" data-share-slug="">
              {splitForMiddleEllipsis(displayUrl(url)).tail}
            </span>
          </code>
          <CopyButton value={url} />
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className={buttonClasses({ variant: "secondary", size: "sm", className: "gap-1.5" })}
          >
            <IconExternal className="size-4" aria-hidden />
            {t("share.open")}
          </a>
          {canManage && draft === null ? (
            <Button
              variant="ghost"
              size="sm"
              leadingIcon={<IconPencil className="size-4" aria-hidden />}
              onClick={() => {
                setDraft(view.slug);
                setError(null);
              }}
            >
              {t("share.changeAddress")}
            </Button>
          ) : null}
        </div>
      )}
      {url && draft !== null ? (
        <form onSubmit={onSubmit} className="space-y-3 rounded-xl border border-line p-4" noValidate>
          <Field label={t("share.addressLabel")} hint={t("share.addressHint")} error={error ? t(error) : undefined}>
            {(control) => (
              <div className="flex items-center gap-2" dir="ltr">
                <span className="shrink-0 font-mono text-sm text-ink-muted">{addressPrefix(url)}</span>
                <Input
                  {...control}
                  dir="ltr"
                  className="font-mono"
                  value={draft}
                  maxLength={SLUG_MAX_LENGTH}
                  autoComplete="off"
                  spellCheck={false}
                  autoFocus
                  onChange={(event) => {
                    setDraft(normalizeSlugInput(event.target.value));
                    setError(null);
                  }}
                />
              </div>
            )}
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm" isLoading={save.isPending}>
              {t("share.saveAddress")}
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setDraft(null)}>
              {t("share.cancel")}
            </Button>
          </div>
        </form>
      ) : null}
      {url && !isWebChatOn ? <Alert tone="warning">{t("share.webChatOff")}</Alert> : null}
    </div>
  );
}
