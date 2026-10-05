import type { Schema } from "@/api/types";
import type { Translator } from "@/i18n/translate";

import { DemoChat } from "../DemoChat";
import { Section } from "../Section";

type DemoCard = Schema<"PublicDemoCard">;

/** A demo business of this kind to chat with, in sandbox. */
export function NicheDemo({ t, demo, messagesPerHour }: { t: Translator["t"]; demo: DemoCard; messagesPerHour: number }) {
  return (
    <Section id="demo" title={t("nichePage.demoTitle")} subtitle={t("nichePage.demoText")} layout="split" glow="right">
      <div className="mx-auto w-full max-w-md overflow-hidden rounded-2xl border border-line bg-surface/95 shadow-2xl">
        <DemoChat demos={[demo]} messagesPerHour={messagesPerHour} />
      </div>
    </Section>
  );
}
