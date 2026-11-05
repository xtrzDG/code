"use client";

/**
 * Step 5, "Who should the assistant call when it needs a person?": the
 * owner in one tap (their sign-in phone by WhatsApp or SMS, their e-mail,
 * or Telegram through a one-time link), or someone else; the people
 * already notified with a way to remove them; and when the assistant calls
 * a person (the niche's usual reasons, changed later in the cabinet).
 * In the edit mode it is "People" of Assistant → Business profile: the
 * same list and choices, the phone for calls that need a person, and the
 * reasons to call one in Rules.
 */

import { useRef, useState } from "react";

import { describeError } from "@/api/errors";
import type { Schema } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconTelegram, IconUsers, IconX } from "@/components/icons";
import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatContactAddress } from "@/lib/phone";
import { isAlreadyContact, ownerChoices, ownerName } from "@/lib/tunnel/contacts";

import { PeopleEditExtras } from "../edit/PeopleEditExtras";
import { StepScreen } from "../StepScreen";
import type { StepContext } from "../flow/stepContext";
import type { StepMode } from "../stepMode";
import { PersonForm } from "./PersonForm";
import { TelegramLinkPanel } from "./TelegramLinkPanel";
import { usePeople } from "./usePeople";

const CHOICE =
  "flex min-h-16 w-full items-start gap-3 rounded-2xl border border-line bg-surface/85 p-3.5 text-start backdrop-blur-sm transition-[border-color,transform] duration-(--motion-base) hover:-translate-y-0.5 hover:border-line-strong disabled:pointer-events-none disabled:opacity-60";

function ContactList({ contacts, onRemove }: { contacts: readonly Schema<"ManagerContactView">[]; onRemove: (contact: Schema<"ManagerContactView">) => void }) {
  const { t } = useI18n();
  return (
    <section aria-labelledby="tunnel-people-current" className="space-y-3">
      <h2 id="tunnel-people-current" className="text-lg font-semibold text-ink">
        {t("tunnelTeam.people.current")}
      </h2>
      <ul className="space-y-2">
        {contacts.map((contact) => (
          <li
            key={`${contact.channel}:${contact.address}`}
            className="flex items-center gap-3 rounded-2xl border border-accent/30 bg-accent-soft/50 py-2 ps-4 pe-2 backdrop-blur-sm"
          >
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold text-ink" dir="auto" data-user-content>
                {contact.name}
              </span>
              <span className="block truncate text-xs text-ink-muted">
                {t(`tunnelTeam.people.by.${contact.channel}`)} · <span dir="ltr" className="whitespace-nowrap">{contact.telegram_username ? `@${contact.telegram_username}` : formatContactAddress(contact.channel, contact.address)}</span>
              </span>
            </span>
            <Button
              variant="ghost"
              size="sm"
              aria-label={t("tunnelTeam.people.remove", { name: contact.name })}
              title={t("tunnelTeam.people.remove", { name: contact.name })}
              onClick={() => onRemove(contact)}
            >
              <IconX className="size-4" aria-hidden />
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function PeopleScreen({ ctx, mode = "tunnel" }: { ctx: StepContext; mode?: StepMode }) {
  const { t } = useI18n();
  const isEdit = mode === "edit";
  const { me, business } = useBusiness();
  const people = usePeople(ctx.businessId);
  const [isOtherOpen, setOtherOpen] = useState(false);
  const otherButton = useRef<HTMLButtonElement>(null);
  const [showError, setShowError] = useState(false);
  const myName = ownerName(me.user, t("tunnelTeam.people.ownerName"));
  const mine = ownerChoices(me.user).filter((choice) => !isAlreadyContact(people.contacts, choice));
  const rules = ctx.wizard.profile.handoff_rules?.length ? ctx.wizard.profile.handoff_rules : (ctx.starters.handoff_rules ?? []);
  const { telegram } = people;
  const hasContacts = people.contacts.length > 0;

  const add = async (contact: Parameters<typeof people.add>[0]) => {
    const saved = await people.add(contact);
    if (saved) {
      setShowError(false);
    }
    return saved;
  };

  /** "Someone else" added: the form closes, the person shows in the list, the focus goes back to the choice. */
  const addOther = async (contact: Parameters<typeof people.add>[0]) => {
    const saved = await add(contact);
    if (saved) {
      setOtherOpen(false);
      otherButton.current?.focus();
    }
    return saved;
  };

  const submit = () => {
    if (!hasContacts) {
      setShowError(true);
      return;
    }
    ctx.refresh();
    ctx.next();
  };

  return (
    <StepScreen
      step="people"
      mode={mode}
      title={isEdit ? t("profileEdit.sections.people.title") : t("tunnelTeam.people.title")}
      text={isEdit ? t("profileEdit.sections.people.text") : t("tunnelTeam.people.text")}
      wide
      actions={isEdit ? {} : { onContinue: submit, onBack: ctx.back, isBusy: people.isSaving }}
    >
      <div className="space-y-8">
        {hasContacts ? <ContactList contacts={people.contacts} onRemove={(contact) => void people.remove(contact)} /> : null}

        <section aria-labelledby="tunnel-people-add" className="space-y-3">
          <h2 id="tunnel-people-add" className="text-lg font-semibold text-ink">
            {t("tunnelTeam.people.add")}
          </h2>
          <div className="grid gap-2.5 sm:grid-cols-2">
            {mine.map((choice) => (
              <button
                key={`${choice.channel}:${choice.address}`}
                type="button"
                disabled={people.isSaving}
                className={CHOICE}
                onClick={() => void add({ name: myName, channel: choice.channel, address: choice.address, language: business.owner_language })}
              >
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-ink">
                    {t("tunnelTeam.people.me")} {t(`tunnelTeam.people.by.${choice.channel}`)}
                  </span>
                  <span className="block truncate text-xs text-ink-muted" dir="ltr">
                    {formatContactAddress(choice.channel, choice.address)}
                  </span>
                </span>
              </button>
            ))}
            {telegram.link ? null : (
              <button
                type="button"
                disabled={telegram.isLinking}
                className={CHOICE}
                onClick={() => void telegram.start(myName)}
              >
                <IconTelegram className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden />
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-ink">{t("tunnelTeam.people.meTelegram")}</span>
                  <span className="block text-xs text-ink-muted">{t("tunnelTeam.people.meTelegramHint")}</span>
                </span>
              </button>
            )}
            <button
              ref={otherButton}
              type="button"
              aria-expanded={isOtherOpen}
              className={cn(CHOICE, isOtherOpen && "border-accent")}
              onClick={() => setOtherOpen((open) => !open)}
            >
              <IconUsers className="mt-0.5 size-5 shrink-0 text-accent" aria-hidden />
              <span className="min-w-0">
                <span className="block text-sm font-semibold text-ink">{t("tunnelTeam.people.someoneElse")}</span>
                <span className="block text-xs text-ink-muted">{t("tunnelTeam.people.someoneElseHint")}</span>
              </span>
            </button>
          </div>

          {telegram.link ? (
            <TelegramLinkPanel link={telegram.link} name={myName} isLinked={telegram.isLinked} onCancel={telegram.cancel} />
          ) : null}
          {telegram.error ? (
            <p className="text-sm text-danger" role="alert">
              {describeError(telegram.error, t).title}
            </p>
          ) : null}
          {isOtherOpen ? (
            <div className="rounded-2xl border border-line bg-surface/85 p-4 backdrop-blur-sm sm:p-5">
              <PersonForm contacts={people.contacts} language={business.owner_language} isSaving={people.isSaving} onAdd={addOther} />
            </div>
          ) : null}
          {showError && !hasContacts ? (
            <p className="text-sm text-danger" role="alert">
              {t("tunnelTeam.people.errors.none")}
            </p>
          ) : null}
        </section>

        {isEdit ? (
          <PeopleEditExtras ctx={ctx} />
        ) : rules.length > 0 ? (
          <section aria-labelledby="tunnel-people-rules" className="space-y-2">
            <h2 id="tunnel-people-rules" className="text-base font-semibold text-ink">
              {t("tunnelTeam.people.handoffTitle")}
            </h2>
            <ul className="list-disc space-y-1 ps-5 text-sm text-ink-muted marker:text-accent">
              {rules.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
            <p className="text-xs text-ink-subtle">{t("tunnelTeam.people.handoffHint")}</p>
          </section>
        ) : null}
      </div>
    </StepScreen>
  );
}
