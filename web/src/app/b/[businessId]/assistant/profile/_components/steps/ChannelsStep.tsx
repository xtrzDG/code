"use client";

import { useRef, useState } from "react";

import type { BusinessLinkKind } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconPlus, IconTrash } from "@/components/icons";
import { Alert, Button, ButtonLink, Checkbox, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { businessPath } from "@/lib/navigation";
import { webLinkSchema } from "@/lib/validation";

import { NicheQuestions, useNicheAnswers } from "../NicheQuestions";
import { StepForm, StepSection } from "../StepForm";
import type { StepProps } from "../types";

const LINK_KINDS: Record<BusinessLinkKind, MessageKey> = {
  menu: "onboarding.channels.linkKinds.menu",
  map: "onboarding.channels.linkKinds.map",
  payment: "onboarding.channels.linkKinds.payment",
  booking_page: "onboarding.channels.linkKinds.booking_page",
  delivery: "onboarding.channels.linkKinds.delivery",
  website: "onboarding.channels.linkKinds.website",
};
const ALL_LINK_KINDS = Object.keys(LINK_KINDS) as BusinessLinkKind[];

interface LinkRow {
  key: string;
  kind: BusinessLinkKind;
  url: string;
}

/** Step 6: links the assistant may send and the call-recording notice. */
export function ChannelsStep({ wizard, step, canEdit, isSaving, isLastStep, onSave, onChange }: StepProps) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const { profile } = wizard;
  const questions = step.questions ?? [];
  const answers = useNicheAnswers(questions, onChange);
  const sequence = useRef(0);

  const [links, setLinks] = useState<LinkRow[]>(() =>
    (profile.links ?? []).map((link) => ({ key: `link-${link.kind}`, kind: link.kind, url: link.url })),
  );
  const [recordingNotice, setRecordingNotice] = useState(profile.is_recording_notice_enabled);
  const [linkErrors, setLinkErrors] = useState<Record<string, MessageKey>>({});

  const usedKinds = new Set(links.map((link) => link.kind));
  const freeKinds = ALL_LINK_KINDS.filter((kind) => !usedKinds.has(kind));

  const updateLink = (key: string, patch: Partial<LinkRow>) => {
    setLinks((current) => current.map((link) => (link.key === key ? { ...link, ...patch } : link)));
    setLinkErrors((current) => {
      const { [key]: _removed, ...rest } = current;
      return rest;
    });
    onChange();
  };

  const submit = (advance: boolean) => {
    const errors: Record<string, MessageKey> = {};
    const filled = links.filter((link) => link.url.trim() !== "");
    for (const link of filled) {
      if (!webLinkSchema.safeParse(link.url).success) {
        errors[link.key] = "validation.url";
      }
    }
    setLinkErrors(errors);
    if (Object.keys(errors).length > 0 || !answers.validate()) {
      return;
    }
    void onSave(
      {
        links: filled.map((link) => ({ kind: link.kind, url: link.url.trim() })),
        is_recording_notice_enabled: recordingNotice,
        answers: answers.payload(),
      },
      { advance },
    );
  };

  return (
    <StepForm
      title={step.title}
      description={step.description}
      canEdit={canEdit}
      isSaving={isSaving}
      isLastStep={isLastStep}
      onSubmit={submit}
    >
      <StepSection title={t("onboarding.channels.links")} hint={t("onboarding.channels.linksHint")}>
        {links.length > 0 ? (
          <ul className="space-y-3">
            {links.map((link) => (
              <li key={link.key} className="space-y-1">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <Select
                    aria-label={t("onboarding.channels.linkKind")}
                    value={link.kind}
                    onChange={(event) => updateLink(link.key, { kind: event.target.value as BusinessLinkKind })}
                    className="sm:w-48"
                  >
                    {ALL_LINK_KINDS.filter((kind) => kind === link.kind || !usedKinds.has(kind)).map((kind) => (
                      <option key={kind} value={kind}>
                        {t(LINK_KINDS[kind])}
                      </option>
                    ))}
                  </Select>
                  <div className="flex min-w-0 flex-1 items-center gap-2">
                    <Input
                      type="url"
                      inputMode="url"
                      aria-label={`${t(LINK_KINDS[link.kind])}: ${t("onboarding.channels.linkUrl")}`}
                      aria-invalid={linkErrors[link.key] ? true : undefined}
                      placeholder="https://"
                      value={link.url}
                      onChange={(event) => updateLink(link.key, { url: event.target.value })}
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      aria-label={`${t("common.remove")}: ${t(LINK_KINDS[link.kind])}`}
                      onClick={() => {
                        setLinks((current) => current.filter((item) => item.key !== link.key));
                        onChange();
                      }}
                    >
                      <IconTrash className="size-4" aria-hidden />
                    </Button>
                  </div>
                </div>
                {linkErrors[link.key] ? <p className="text-sm text-danger">{t(linkErrors[link.key] ?? "validation.url")}</p> : null}
              </li>
            ))}
          </ul>
        ) : null}
        {freeKinds.length > 0 ? (
          <Button
            variant="secondary"
            size="sm"
            leadingIcon={<IconPlus className="size-4" aria-hidden />}
            onClick={() => {
              const kind = freeKinds[0];
              if (kind) {
                sequence.current += 1;
                setLinks((current) => [...current, { key: `new-${sequence.current}`, kind, url: "" }]);
              }
            }}
          >
            {t("onboarding.channels.addLink")}
          </Button>
        ) : null}
      </StepSection>

      <Checkbox
        id="recording-notice"
        checked={recordingNotice}
        onChange={(event) => {
          setRecordingNotice(event.target.checked);
          onChange();
        }}
        label={<span className="font-medium">{t("onboarding.channels.recordingNotice")}</span>}
        description={t("onboarding.channels.recordingNoticeHint")}
      />

      <Alert
        tone="info"
        action={
          <ButtonLink href={businessPath(business.id, "assistant/channels")} variant="secondary" size="sm">
            {t("onboarding.channels.openChannels")}
          </ButtonLink>
        }
      >
        {t("onboarding.channels.channelsHint")}
      </Alert>

      <NicheQuestions questions={questions} state={answers} />
    </StepForm>
  );
}
