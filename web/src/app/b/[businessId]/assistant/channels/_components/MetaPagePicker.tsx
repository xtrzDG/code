"use client";

import { useId, useState } from "react";

import { Alert, Button, Fieldset, Radio } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { pageTitle, type MetaChannel, type MetaPage } from "../_lib/metaSignIn";

/**
 * The pages a Facebook sign-in brought back, to connect one to Messenger or
 * Instagram. For Instagram only pages linked to an Instagram professional
 * account can be chosen (the others stay listed, greyed, with why).
 */
export function MetaPagePicker({
  kind,
  pages,
  pickingId,
  onPick,
}: {
  kind: Exclude<MetaChannel, "whatsapp">;
  pages: readonly MetaPage[];
  /** The page being connected now, if any. */
  pickingId: string | null;
  onPick: (pageId: string) => void;
}) {
  const { t } = useI18n();
  const name = useId();
  const canPick = (page: MetaPage) => kind !== "instagram" || page.has_instagram;
  const [chosen, setChosen] = useState<string | null>(() => pages.find(canPick)?.page_id ?? null);

  if (pages.length === 0) {
    return <Alert tone="warning">{t("metaConnect.pages.none")}</Alert>;
  }

  const instagramLine = (page: MetaPage) => {
    if (!page.has_instagram) {
      return t("metaConnect.pages.noInstagram");
    }
    return page.instagram_username
      ? t("metaConnect.pages.instagram", { username: page.instagram_username })
      : t("metaConnect.pages.instagramNoName");
  };

  return (
    <Fieldset
      legend={t("metaConnect.pages.title")}
      hint={kind === "instagram" ? t("metaConnect.pages.instagramHint") : t("metaConnect.pages.hint")}
    >
      <ul className="max-h-72 space-y-2 overflow-y-auto">
        {pages.map((page) => (
          <li key={page.page_id} className="rounded-lg border border-line bg-surface px-3 py-2.5">
            <Radio
              name={name}
              value={page.page_id}
              checked={chosen === page.page_id}
              disabled={!canPick(page) || pickingId !== null}
              onChange={() => setChosen(page.page_id)}
              label={<span dir="auto">{pageTitle(page)}</span>}
              description={<span dir="auto">{instagramLine(page)}</span>}
            />
          </li>
        ))}
      </ul>
      <Button
        onClick={() => (chosen ? onPick(chosen) : undefined)}
        disabled={chosen === null}
        isLoading={pickingId !== null}
        loadingText={t("metaConnect.pages.connecting")}
      >
        {t("metaConnect.pages.connect")}
      </Button>
    </Fieldset>
  );
}
