"use client";

import { IconLink, IconUpload } from "@/components/icons";
import { Alert, Button, Card, Field, Input, Radio } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import type { MenuLinkProblemCode } from "@/lib/knowledge/menuImport";

import type { MenuSource } from "../_lib/useMenuSource";
import { MenuFileDrop } from "./MenuFileDrop";

const LINK_PROBLEM_TEXTS: Record<MenuLinkProblemCode, MessageKey> = {
  menu_link_invalid: "knowledge.import.errors.linkInvalid",
  menu_link_unreachable: "knowledge.import.errors.linkUnreachable",
  menu_link_unreadable: "knowledge.import.errors.linkUnreadable",
};

/** The first stage of a menu import: choose a file or type a link, then read it. */
export function MenuSourceForm({ source }: { source: MenuSource }) {
  const { t } = useI18n();
  const { inputId, linkProblem, readFailure, isReading } = source;

  return (
    <Card title={t("knowledge.import.title")} description={t("knowledge.import.description")}>
      <form onSubmit={(event) => void source.read(event)} noValidate className="space-y-5">
        <fieldset className="space-y-2">
          <legend className="mb-2 text-sm font-medium text-ink">{t("knowledge.import.sourceLabel")}</legend>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            <Radio
              id={`${inputId}-source-file`}
              name="menu-source"
              label={t("knowledge.import.sourceFile")}
              checked={source.source === "file"}
              onChange={() => source.chooseSource("file")}
            />
            <Radio
              id={`${inputId}-source-link`}
              name="menu-source"
              label={t("knowledge.import.sourceLink")}
              checked={source.source === "link"}
              onChange={() => source.chooseSource("link")}
            />
          </div>
        </fieldset>

        {source.source === "file" ? (
          <MenuFileDrop source={source} />
        ) : (
          <Field
            label={t("knowledge.import.link")}
            hint={t("knowledge.import.linkHint")}
            error={source.linkError && t(source.linkError)}
            required
          >
            {(control) => (
              <Input
                {...control}
                type="url"
                inputMode="url"
                autoComplete="url"
                placeholder="https://"
                value={source.link}
                onChange={(event) => source.changeLink(event.target.value)}
              />
            )}
          </Field>
        )}

        {linkProblem ? (
          <Alert tone="danger" title={t("knowledge.import.errors.readFailed")}>
            {linkProblem.status !== null
              ? t("knowledge.import.errors.linkHttpStatus", { status: linkProblem.status })
              : t(LINK_PROBLEM_TEXTS[linkProblem.code])}
          </Alert>
        ) : null}
        {readFailure ? (
          <Alert tone="danger" title={t("knowledge.import.errors.readFailed")}>
            {[readFailure.title, readFailure.detail, readFailure.requestId ? t("common.requestId", { id: readFailure.requestId }) : null]
              .filter(Boolean)
              .join(" ")}
          </Alert>
        ) : null}

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" isLoading={isReading} loadingText={t("knowledge.import.reading")} leadingIcon={source.source === "file" ? <IconUpload className="size-4" aria-hidden /> : <IconLink className="size-4" aria-hidden />}>
            {t("knowledge.import.read")}
          </Button>
          {isReading ? <p className="text-sm text-ink-muted" role="status">{t("knowledge.import.readingHint")}</p> : null}
        </div>
        <p className="text-sm text-ink-subtle">{t("knowledge.import.draftsNote")}</p>
      </form>
    </Card>
  );
}
