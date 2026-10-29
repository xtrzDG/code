"use client";

import Link from "next/link";
import { useId, useState, type FormEvent, type ReactNode } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { Switch } from "@/components/content/Switch";
import { IconBell, IconInbox, IconTelegram, IconWhatsApp } from "@/components/icons";
import { Button, Field, Input, Select } from "@/components/ui";
import {
  canTurnOn,
  normalizeWhatsAppNumber,
  telegramChatFor,
  whatsappNumberFor,
  withChannel,
  type DigestChannel,
  type DigestPreferencesView,
} from "@/components/value/digestChannelsModel";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";
import { formatPhone } from "@/lib/phone";

/** A change of where the summaries arrive, as the PUT takes it. */
export interface DigestChannelChange {
  channels: DigestChannel[];
  telegram_chat?: string;
  whatsapp_number?: string;
}

/**
 * Where the owner's summaries arrive: the sign-in e-mail, the devices with
 * notifications on, a Telegram chat linked through the platform bot (the
 * whole report) and WhatsApp from the platform's number (a short summary
 * with a link). A channel that cannot reach the owner is not offered.
 */
export function DigestChannelsSection({
  preferences,
  isSaving,
  onSave,
}: {
  preferences: DigestPreferencesView;
  isSaving: boolean;
  /** Saves the change; resolves to whether the API took it. */
  onSave: (change: DigestChannelChange) => Promise<boolean>;
}) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const headingId = useId();
  const channels = preferences.channels;
  const isOn = (channel: DigestChannel) => channels.includes(channel);
  // The number being typed (null: not editing; WhatsApp waits for a number to switch on).
  const [whatsappDraft, setWhatsappDraft] = useState<string | null>(null);
  const [numberError, setNumberError] = useState<string | null>(null);
  const telegramChat = telegramChatFor(preferences);

  const toggle = (channel: DigestChannel, turnOn: boolean) => {
    const next = withChannel(channels, channel, turnOn);
    if (!turnOn) {
      void onSave({ channels: next });
    } else if (channel === "telegram" && telegramChat) {
      void onSave({ channels: next, telegram_chat: telegramChat });
    } else if (channel === "whatsapp") {
      const number = normalizeWhatsAppNumber(whatsappNumberFor(preferences));
      if (number) {
        void onSave({ channels: next, whatsapp_number: number });
      } else {
        setWhatsappDraft(whatsappNumberFor(preferences));
      }
    } else {
      void onSave({ channels: next });
    }
  };

  const saveNumber = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const number = normalizeWhatsAppNumber(whatsappDraft ?? whatsappNumberFor(preferences));
    if (!number) {
      setNumberError(t("digestChannels.invalidNumber"));
      return;
    }
    setNumberError(null);
    if (await onSave({ channels: withChannel(channels, "whatsapp", true), whatsapp_number: number })) {
      setWhatsappDraft(null);
    }
  };

  const emailHint = !preferences.email
    ? t("digestChannels.emailMissing")
    : preferences.is_email_ready
      ? t("digestChannels.emailTo", { email: preferences.email })
      : t("digestChannels.emailNotReady");
  const telegramHint = !preferences.is_telegram_ready
    ? t("digestChannels.telegramNotReady")
    : preferences.telegram_chats.length === 0
      ? t("digestChannels.telegramNoChats")
      : t("digestChannels.telegramHint");
  const showsNumber = isOn("whatsapp") || whatsappDraft !== null;

  return (
    <section aria-labelledby={headingId} className="space-y-3 border-t border-line pt-4">
      <h3 id={headingId} className="text-sm font-semibold text-ink">
        {t("digestChannels.title")}
      </h3>
      <ul className="space-y-3.5">
        <ChannelRow
          icon={<IconInbox className="size-4" aria-hidden />}
          label={t("digestChannels.email")}
          hint={emailHint}
          checked={isOn("email")}
          disabled={isSaving || (!isOn("email") && !canTurnOn(preferences, "email"))}
          onChange={(value) => toggle("email", value)}
        />
        <ChannelRow
          icon={<IconBell className="size-4" aria-hidden />}
          label={t("digestChannels.push")}
          hint={preferences.device_count > 0 ? tp("digestChannels.devices", preferences.device_count) : t("digestChannels.noDevices")}
          checked={isOn("push")}
          disabled={isSaving}
          onChange={(value) => toggle("push", value)}
        >
          <Link href={businessPath(business.id, "settings/notifications")} className="text-xs font-medium text-accent hover:underline">
            {t("digestChannels.manageDevices")}
          </Link>
        </ChannelRow>
        <ChannelRow
          icon={<IconTelegram className="size-4" aria-hidden />}
          label={t("digestChannels.telegram")}
          hint={telegramHint}
          checked={isOn("telegram")}
          disabled={isSaving || (!isOn("telegram") && !canTurnOn(preferences, "telegram"))}
          onChange={(value) => toggle("telegram", value)}
        >
          {preferences.is_telegram_ready && preferences.telegram_chats.length === 0 ? (
            <Link href={businessPath(business.id, "assistant/channels")} className="text-xs font-medium text-accent hover:underline">
              {t("digestChannels.openChannels")}
            </Link>
          ) : isOn("telegram") && preferences.telegram_chats.length > 1 ? (
            <Field label={t("digestChannels.telegramChat")}>
              {(control) => (
                <Select
                  {...control}
                  value={telegramChat ?? ""}
                  disabled={isSaving}
                  onChange={(event) => void onSave({ channels, telegram_chat: event.target.value })}
                >
                  {preferences.telegram_chats.map((chat) => (
                    <option key={chat.address} value={chat.address}>
                      {chat.username ? `${chat.name} (@${chat.username})` : chat.name}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          ) : null}
        </ChannelRow>
        <ChannelRow
          icon={<IconWhatsApp className="size-4" aria-hidden />}
          label={t("digestChannels.whatsapp")}
          hint={preferences.is_whatsapp_ready ? t("digestChannels.whatsappHint") : t("digestChannels.whatsappNotReady")}
          checked={isOn("whatsapp")}
          disabled={isSaving || (!isOn("whatsapp") && !canTurnOn(preferences, "whatsapp"))}
          onChange={(value) => toggle("whatsapp", value)}
        >
          {showsNumber ? (
            <form onSubmit={(event) => void saveNumber(event)} className="space-y-2" noValidate>
              <Field label={t("digestChannels.whatsappNumber")} hint={t("digestChannels.whatsappNumberHint")} error={numberError}>
                {(control) => (
                  <Input
                    {...control}
                    type="tel"
                    inputMode="tel"
                    autoComplete="tel"
                    dir="ltr"
                    value={whatsappDraft ?? formatPhone(whatsappNumberFor(preferences))}
                    onChange={(event) => setWhatsappDraft(event.target.value)}
                  />
                )}
              </Field>
              <Button type="submit" size="sm" variant="secondary" disabled={isSaving || whatsappDraft === null}>
                {t("digestChannels.save")}
              </Button>
            </form>
          ) : null}
        </ChannelRow>
      </ul>
    </section>
  );
}

/** One channel: its switch, why it is (not) offered, and its settings under it. */
function ChannelRow({
  icon,
  label,
  hint,
  checked,
  disabled,
  onChange,
  children,
}: {
  icon: ReactNode;
  label: string;
  hint: string;
  checked: boolean;
  disabled: boolean;
  onChange: (checked: boolean) => void;
  children?: ReactNode;
}) {
  const hintId = useId();
  return (
    <li className="space-y-2">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 gap-2.5">
          <span className="mt-0.5 shrink-0 text-ink-muted">{icon}</span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-ink">{label}</p>
            <p id={hintId} className="text-xs break-words text-ink-muted">
              {hint}
            </p>
          </div>
        </div>
        <Switch label={label} checked={checked} disabled={disabled} describedBy={hintId} onChange={onChange} />
      </div>
      {children ? <div className="ps-6.5">{children}</div> : null}
    </li>
  );
}
