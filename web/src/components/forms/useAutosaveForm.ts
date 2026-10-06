"use client";

/**
 * A settings form that saves itself, the way the business profile does:
 *
 *     const form = useAutosaveForm({
 *       stored: settings.data,
 *       toForm: callSettingsForm,
 *       toBody: (values) => callSettingsBody(values),
 *       save: (body) => save.run(body),
 *       onSaved: (stored) => settings.setData(stored),
 *       undo: (before, after) => (before.isTextBackEnabled && !after.isTextBackEnabled ? t("…off") : null),
 *     });
 *     <Switch checked={form.values.isTextBackEnabled} onChange={(on) => form.update("isTextBackEnabled", on)} />
 *     <Input value={form.values.templateName} onChange={(e) => form.type("templateName", e.target.value)} onBlur={form.flush} />
 *     <SavePill state={form.fieldState("templateName")} onRetry={form.retry} />
 *
 * Switches and lists save at once (`update`); text a moment after the last
 * key (`type`) and at once when the field is left (`flush`). Each field
 * says "Saving…", "Saved" or "Not saved" by itself (SavePill); a failure
 * for want of a connection is tried again; a save refused because someone
 * saved since is rebased (`conflict`); a change that deletes data waits
 * for a confirmation (`needsConfirmation`); switching something off offers
 * Undo (`undo`). What is unsaved is saved when the form goes away.
 */

import { useEffect, useState, useSyncExternalStore } from "react";

import { useToast, type ToastTitle } from "@/components/ui";

import { AutosaveEngine } from "./autosaveEngine";
import type { AutosaveConfig, FieldSaveState } from "./autosaveTypes";
import { createSaveCounter, type SaveState } from "./saveTracking";

/** How long typed text waits before it is saved. */
const TYPING_DELAY_MS = 800;

const IDLE: FieldSaveState = { status: "idle", savedAt: null };

export interface AutosaveFormOptions<Form extends object, Stored, Body> extends AutosaveConfig<Form, Stored, Body> {
  /** What the server holds (a newer copy from elsewhere is taken while nothing is being saved). */
  stored: Stored;
  /** An Undo toast for a change that switches something off: its title, or null for none. */
  undo?: (before: Form, after: Form) => ToastTitle | null;
}

export function useAutosaveForm<Form extends object, Stored, Body>(options: AutosaveFormOptions<Form, Stored, Body>) {
  const toast = useToast();
  const [state, setState] = useState<SaveState>("idle");
  const [track] = useState(() => createSaveCounter(setState));
  const [engine] = useState(() => new AutosaveEngine<Form, Stored, Body>(options.stored, options.toForm));

  // The rules close over the page's state: given again after every render.
  useEffect(() => {
    engine.configure({
      ...options,
      save: (body, base) => {
        const result = options.save(body, base);
        void track(result.then((answer) => answer.ok));
        return result;
      },
      onSaved: (stored, before, after) => {
        options.onSaved?.(stored, before, after);
        const title = options.undo?.(before, after);
        if (title) {
          toast.undoable(title, () => engine.revert(before, after));
        }
      },
    });
  });
  const snapshot = useSyncExternalStore(engine.subscribe, engine.getSnapshot, engine.getSnapshot);

  useEffect(() => {
    engine.adopt(options.stored);
  }, [engine, options.stored]);

  // Closing the tab with a change still unsaved asks first; leaving the page saves it.
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (engine.getSnapshot().isBusy) {
        void engine.flush();
        event.preventDefault();
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => {
      window.removeEventListener("beforeunload", warn);
      void engine.flush();
    };
  }, [engine]);

  return {
    values: snapshot.form,
    stored: snapshot.base,
    /** "Saving…", "Saved", "Not saved" of the whole form (its last saves). */
    state,
    isBusy: snapshot.isBusy,
    error: snapshot.error,
    conflicts: snapshot.conflicts,
    isReloadFailed: snapshot.isReloadFailed,
    confirming: snapshot.confirming,
    /** A switch, a choice, a list: saved at once. */
    update: <Field extends keyof Form>(field: Field, value: Form[Field]) =>
      engine.change({ [field]: value } as unknown as Partial<Form>, 0),
    /** Text: saved a moment after the last key (and at once on `flush`). */
    type: <Field extends keyof Form>(field: Field, value: Form[Field]) =>
      engine.change({ [field]: value } as unknown as Partial<Form>, TYPING_DELAY_MS),
    flush: () => void engine.flush(),
    retry: () => void engine.retry(),
    confirm: () => engine.confirm(),
    cancelConfirmation: () => engine.cancelConfirmation(),
    reloadStored: () => engine.reloadStored(),
    fieldState: (field: keyof Form): FieldSaveState => snapshot.fields[field] ?? IDLE,
  };
}
