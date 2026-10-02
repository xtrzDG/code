"use client";

import Link from "next/link";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconCopy } from "@/components/content/icons";
import { Button, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { AssistantVersionDetails } from "@/lib/assistant/versions";
import { businessPath } from "@/lib/navigation";

import { TOOL_LABELS } from "../../../_lib/toolLabels";

/** The business facts the version was built from. */
export function FactsPanel({ details }: { details: AssistantVersionDetails }) {
  const { t } = useI18n();
  return details.facts.length === 0 ? (
    <p className="text-sm text-ink-muted">{t("assistant.detail.noFacts")}</p>
  ) : (
    <div className="space-y-3">
      <p className="text-sm text-ink-muted">{t("assistant.detail.factsHint")}</p>
      <dl className="divide-y divide-line rounded-xl border border-line">
        {details.facts.map((fact) => (
          <div key={fact.key} className="grid gap-1 px-4 py-3 sm:grid-cols-3 sm:gap-4">
            <dt className="text-sm font-medium text-ink-muted">{fact.label}</dt>
            <dd className="text-sm break-words whitespace-pre-line text-ink sm:col-span-2" dir="auto">
              {fact.value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

/** The version's instruction (system prompt), with a copy button. */
export function InstructionPanel({ details }: { details: AssistantVersionDetails }) {
  const { t } = useI18n();
  const toast = useToast();
  const copyInstruction = async () => {
    try {
      await navigator.clipboard.writeText(details.prompt_text);
      toast.success(t("assistant.detail.copied"));
    } catch {
      toast.show({ tone: "error", title: t("assistant.detail.copyFailed") });
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-muted">{t("assistant.detail.instructionHint")}</p>
        <Button variant="secondary" size="sm" leadingIcon={<IconCopy className="size-4" aria-hidden />} onClick={() => void copyInstruction()}>
          {t("assistant.detail.copy")}
        </Button>
      </div>
      <pre
        className="max-h-[32rem] overflow-auto rounded-xl border border-line bg-surface-muted p-4 text-xs leading-relaxed break-words whitespace-pre-wrap text-ink"
        dir="auto"
        tabIndex={0}
        aria-label={t("assistant.detail.tabs.instruction")}
      >
        {details.prompt_text}
      </pre>
    </div>
  );
}

/** The tools the version may call and the channels it answers in. */
export function ToolsPanel({ details }: { details: AssistantVersionDetails }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-ink">{t("assistant.detail.toolsTitle")}</h3>
        <ul className="grid gap-3 sm:grid-cols-2">
          {details.tools.map((tool) => (
            <li key={tool} className="rounded-xl border border-line px-4 py-3">
              <p className="text-sm font-medium text-ink">{t(TOOL_LABELS[tool].name)}</p>
              <p className="mt-0.5 text-sm text-ink-muted">{t(TOOL_LABELS[tool].description)}</p>
            </li>
          ))}
        </ul>
      </section>
      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-ink">{t("assistant.detail.channelsTitle")}</h3>
        <ul className="divide-y divide-line rounded-xl border border-line text-sm">
          <li className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
            <span className="text-ink">{t("assistant.detail.chatChannels")}</span>
            <span className="text-ink-muted">{t("assistant.detail.chatChannelsValue")}</span>
          </li>
          <li className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
            <span className="text-ink">{t("assistant.detail.voice")}</span>
            <span className="text-ink-muted">
              {details.is_voice_enabled
                ? details.voice_agent_id
                  ? t("assistant.detail.voiceReady")
                  : t("assistant.detail.voiceIncluded")
                : t("assistant.detail.voiceOff")}
            </span>
          </li>
        </ul>
        <Link href={businessPath(business.id, "channels")} className="inline-block text-sm font-medium text-accent hover:underline">
          {t("assistant.detail.openChannels")}
        </Link>
      </section>
    </div>
  );
}
