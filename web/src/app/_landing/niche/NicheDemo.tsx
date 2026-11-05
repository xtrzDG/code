import type { Schema } from "@/api/types";
import type { Translator } from "@/i18n/translate";

import { DemoChat } from "../DemoChat";

type DemoCard = Schema<"PublicDemoCard">;

/** A demo business of this kind to chat with in sandbox, with a line on what it is. */
export function NicheDemo({ t, demo, messagesPerHour }: { t: Translator["t"]; demo: DemoCard; messagesPerHour: number }) {
  return (
    <div id="demo" className="scroll-mt-20 space-y-3">
      <div className="space-y-1">
        <h2 className="text-base font-semibold text-ink">{t("nichePage.demoTitle")}</h2>
        <p className="text-sm text-pretty text-ink-muted">{t("nichePage.demoText")}</p>
      </div>
      <div className="overflow-hidden rounded-2xl border border-line bg-surface/95 shadow-2xl backdrop-blur">
        <DemoChat demos={[demo]} messagesPerHour={messagesPerHour} />
      </div>
    </div>
  );
}
