"use client";

import { useState, type FormEvent } from "react";

import { describeError } from "@/api/errors";
import { IconGlobe } from "@/components/icons";
import { Alert, Button, Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { normalizeWebsiteAddress, startProblemText, type ProblemText } from "@/lib/knowledge/websiteImport";

/**
 * The address of the business's website and the button that starts reading
 * it. The address is checked for shape here; whether the site may be read
 * (public, reachable) is the API's answer, shown under the field.
 */
export function WebsiteImportForm({
  initialUrl,
  failure,
  startError,
  isStarting,
  onStart,
}: {
  /** The address to offer: the last import's, or the profile's website link. */
  initialUrl: string;
  /** Why the last import could not read the site. */
  failure: ProblemText | null;
  startError: unknown;
  isStarting: boolean;
  onStart: (url: string) => void;
}) {
  const { t } = useI18n();
  // Null until the owner types: the offered address may arrive after the form.
  const [typed, setTyped] = useState<string | null>(null);
  const [addressError, setAddressError] = useState<MessageKey | null>(null);
  const address = typed ?? initialUrl;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (address.trim() === "") {
      setAddressError("knowledge.website.errors.required");
      return;
    }
    const url = normalizeWebsiteAddress(address);
    if (url === null) {
      setAddressError("knowledge.website.errors.address");
      return;
    }
    setAddressError(null);
    setTyped(url);
    onStart(url);
  };

  const refusal = startError ? startProblemText(startError) : null;
  const refusalText = refusal
    ? t(refusal.key, refusal.values)
    : startError
      ? describeError(startError, t).title
      : null;

  return (
    <form onSubmit={submit} noValidate className="space-y-5">
      <Field
        label={t("knowledge.website.address")}
        hint={t("knowledge.website.addressHint")}
        error={addressError ? t(addressError) : refusalText}
        required
      >
        {(control) => (
          <Input
            {...control}
            type="url"
            inputMode="url"
            autoComplete="url"
            dir="ltr"
            placeholder="https://"
            value={address}
            onChange={(event) => {
              setTyped(event.target.value);
              setAddressError(null);
            }}
          />
        )}
      </Field>

      {failure && !startError ? (
        <Alert tone="danger" title={t("knowledge.website.errors.failedTitle")}>
          {t(failure.key, failure.values)}
        </Alert>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="submit"
          isLoading={isStarting}
          loadingText={t("knowledge.website.starting")}
          leadingIcon={<IconGlobe className="size-4" aria-hidden />}
        >
          {t("knowledge.website.start")}
        </Button>
      </div>
      <p className="text-sm text-ink-subtle">{t("knowledge.website.safety")}</p>
    </form>
  );
}
