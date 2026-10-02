"use client";

import Link from "next/link";
import { useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconCopy } from "@/components/icons";
import { Button, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { cn } from "@/lib/cn";
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

type InstructionMedium = "chat" | "phone";

/**
 * The version's instructions (system prompts) with a copy button: the chat
 * one, and for a version with voice the phone one (spoken prices and
 * hours, no links), chosen with a small switch.
 */
export function InstructionPanel({ details }: { details: AssistantVersionDetails }) {
  const { t } = useI18n();
  const toast = useToast();
  const [medium, setMedium] = useState<InstructionMedium>("chat");
  const phoneText = details.phone_prompt_text ?? null;
  const shown: InstructionMedium = phoneText === null ? "chat" : medium;
  const text = shown === "phone" && phoneText !== null ? phoneText : details.prompt_text;
  const copyInstruction = async () => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(t("assistant.detail.copied"));
    } catch {
      toast.show({ tone: "error", title: t("assistant.detail.copyFailed") });
    }
  };

  return (
    <div className="space-y-3">
      {phoneText !== null ? <MediumSwitch value={shown} onChange={setMedium} /> : null}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-muted">
          {t(shown === "phone" ? "assistant.detail.phoneInstructionHint" : "assistant.detail.instructionHint")}
        </p>
        <Button variant="secondary" size="sm" leadingIcon={<IconCopy className="size-4" aria-hidden />} onClick={() => void copyInstruction()}>
          {t("assistant.detail.copy")}
        </Button>
      </div>
      <pre
        key={shown}
        className="max-h-[32rem] animate-settle overflow-auto rounded-xl border border-line bg-surface-muted p-4 text-xs leading-relaxed break-words whitespace-pre-wrap text-ink"
        dir="auto"
        tabIndex={0}
        aria-label={t(shown === "phone" ? "assistant.detail.instructionPhone" : "assistant.detail.tabs.instruction")}
      >
        {text}
      </pre>
    </div>
  );
}

/** Chat or phone: which instruction of the version is shown. */
function MediumSwitch({ value, onChange }: { value: InstructionMedium; onChange: (medium: InstructionMedium) => void }) {
  const { t } = useI18n();
  const options: readonly { medium: InstructionMedium; label: MessageKey }[] = [
    { medium: "chat", label: "assistant.detail.instructionChat" },
    { medium: "phone", label: "assistant.detail.instructionPhone" },
  ];
  return (
    <div role="group" aria-label={t("assistant.detail.instructionFor")} className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-ink-muted">{t("assistant.detail.instructionFor")}</span>
      <div className="inline-flex rounded-xl border border-line bg-surface-muted p-0.5">
        {options.map((option) => (
          <button
            key={option.medium}
            type="button"
            aria-pressed={value === option.medium}
            onClick={() => onChange(option.medium)}
            className={cn(
              "inline-flex min-h-9 items-center rounded-lg px-3 text-sm font-medium transition-colors",
              value === option.medium ? "bg-surface text-ink shadow-sm" : "text-ink-muted hover:text-ink",
            )}
          >
            {t(option.label)}
          </button>
        ))}
      </div>
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
