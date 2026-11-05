/**
 * The save loop of a settings form that saves itself, apart from React
 * (useAutosaveForm.ts binds it): a change waits a moment (text) or goes at
 * once (a switch, a list), one save runs at a time and what changed
 * meanwhile goes in the next one, a field that is not valid yet waits with
 * its stored value in the request, a save that failed for want of a
 * connection is tried again a few times, a save refused because someone
 * saved since is put on top of what is stored now, and a change that needs
 * a confirmation (a shorter retention deletes data) waits for it.
 */

import type { ApiError } from "@/api/errors";

import { changedFields, isTransientFailure, systemClock, type AutosaveClock } from "./autosaveParts";
import type { AutosaveConfig, AutosaveSnapshot, FieldSaveStatus } from "./autosaveTypes";

const DEFAULT_RETRY_DELAYS_MS = [2_000, 6_000, 15_000] as const;
/** Refused as stale this many times in a row: stop and show it, rather than loop. */
const MAX_CONFLICT_ROUNDS = 2;

export class AutosaveEngine<Form extends object, Stored, Body> {
  private snapshot: AutosaveSnapshot<Form, Stored>;
  private readonly listeners = new Set<() => void>();
  private readonly versions = new Map<keyof Form, number>();
  private timer: unknown = null;
  private retryTimer: unknown = null;
  private running: Promise<void> | null = null;
  private again = false;
  private retries = 0;
  private conflictRounds = 0;
  private confirmed: string | null = null;
  private settings: AutosaveConfig<Form, Stored, Body> | null = null;

  constructor(
    stored: Stored,
    toForm: (stored: Stored) => Form,
    private readonly clock: AutosaveClock = systemClock,
  ) {
    this.snapshot = {
      form: toForm(stored),
      base: stored,
      fields: {},
      error: null,
      conflicts: [],
      isReloadFailed: false,
      confirming: [],
      isBusy: false,
    };
  }

  getSnapshot = (): AutosaveSnapshot<Form, Stored> => this.snapshot;

  /** The form's rules and its save (given again on every render: they close over the page's state). */
  configure(settings: AutosaveConfig<Form, Stored, Body>): void {
    this.settings = settings;
  }

  private config(): AutosaveConfig<Form, Stored, Body> {
    if (!this.settings) {
      throw new Error("AutosaveEngine.configure() was not called.");
    }
    return this.settings;
  }

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  /** A change of some fields; saved after `delayMs` (0: at once) unless more changes come first. */
  change(patch: Partial<Form>, delayMs: number): void {
    const keys = Object.keys(patch) as (keyof Form)[];
    for (const key of keys) {
      this.versions.set(key, (this.versions.get(key) ?? 0) + 1);
    }
    this.update({
      form: { ...this.snapshot.form, ...patch },
      conflicts: this.snapshot.conflicts.filter((field) => !keys.includes(field)),
      confirming: [],
    });
    this.schedule(delayMs);
  }

  /** Put back the fields a save changed (Undo). */
  revert(before: Form, after: Form): void {
    const fields = changedFields(before, after);
    this.change(Object.fromEntries(fields.map((field) => [field, before[field]])) as Partial<Form>, 0);
  }

  /** Save what is not saved yet now, and wait until every save of the form is done. */
  async flush(): Promise<void> {
    this.clearTimers();
    await this.run();
  }

  /** The owner confirmed the change that waited (a shorter period): save it. */
  confirm(): Promise<void> {
    this.confirmed = JSON.stringify(this.snapshot.form);
    this.update({ confirming: [] });
    return this.flush();
  }

  /** The owner did not confirm: those fields go back to what is stored. */
  cancelConfirmation(): void {
    const stored = this.config().toForm(this.snapshot.base);
    const form = { ...this.snapshot.form };
    for (const field of this.snapshot.confirming) {
      form[field] = stored[field];
    }
    this.update({ form, confirming: [] });
  }

  /** Load what is stored now after a reload failed, and save the owner's other changes on top. */
  async reloadStored(): Promise<boolean> {
    const conflict = this.config().conflict;
    if (!conflict) {
      return false;
    }
    const latest = await conflict.reload();
    if (!latest.ok) {
      this.update({ error: latest.error });
      return false;
    }
    this.rebaseOn(latest.data);
    await this.flush();
    return true;
  }

  /** A copy of the stored data from elsewhere: taken while nothing is being saved, or when it only moves the revision. */
  adopt(stored: Stored): void {
    const { base, form } = this.snapshot;
    const config = this.config();
    if (stored === base || (config.isNewer && !config.isNewer(stored, base))) {
      return;
    }
    const isIdle = !this.running && this.timer === null && changedFields(form, config.toForm(base)).length === 0;
    if (isIdle) {
      this.update({ base: stored, form: config.toForm(stored) });
    } else if (changedFields(config.toForm(stored), config.toForm(base)).length === 0) {
      this.update({ base: stored });
    }
  }

  private update(patch: Partial<AutosaveSnapshot<Form, Stored>>): void {
    this.snapshot = { ...this.snapshot, ...patch };
    for (const listener of this.listeners) {
      listener();
    }
  }

  private setFields(fields: readonly (keyof Form)[], status: FieldSaveStatus): void {
    if (fields.length === 0) {
      return;
    }
    const next = { ...this.snapshot.fields };
    for (const field of fields) {
      next[field] = { status, savedAt: status === "saved" ? this.clock.now() : (next[field]?.savedAt ?? null) };
    }
    this.update({ fields: next });
  }

  private clearTimers(): void {
    for (const timer of [this.timer, this.retryTimer]) {
      if (timer !== null) {
        this.clock.clearTimeout(timer);
      }
    }
    this.timer = null;
    this.retryTimer = null;
  }

  private schedule(delayMs: number): void {
    this.clearTimers();
    this.retries = 0;
    this.timer = this.clock.setTimeout(() => {
      this.timer = null;
      void this.run();
    }, delayMs);
    this.update({ isBusy: true });
  }

  private run(): Promise<void> {
    if (this.running) {
      this.again = true;
      return this.running;
    }
    this.update({ isBusy: true });
    this.running = (async () => {
      try {
        do {
          this.again = false;
          await this.saveOnce();
        } while (this.again);
      } finally {
        this.running = null;
        this.update({ isBusy: this.timer !== null || this.retryTimer !== null });
      }
    })();
    return this.running;
  }

  private rebaseOn(latest: Stored): (keyof Form)[] {
    const conflict = this.config().conflict;
    const rebased = conflict ? conflict.rebase(this.snapshot.base, latest, this.snapshot.form) : { form: this.snapshot.form, conflicts: [] };
    this.update({
      base: latest,
      form: rebased.form,
      conflicts: [...new Set([...this.snapshot.conflicts, ...rebased.conflicts])],
      isReloadFailed: false,
    });
    this.setFields(rebased.conflicts, "idle");
    return rebased.conflicts;
  }

  private async saveOnce(): Promise<void> {
    const config = this.config();
    const { form, base } = this.snapshot;
    const stored = config.toForm(base);
    // A field that is not valid yet keeps its stored value in this save.
    const ready = { ...form };
    for (const field of config.invalidFields?.(form) ?? []) {
      ready[field] = stored[field];
    }
    const fields = changedFields(ready, stored);
    const body = fields.length === 0 ? null : config.toBody(ready, base);
    if (body === null) {
      return;
    }
    const confirming = config.needsConfirmation?.(ready, base) ?? [];
    if (confirming.length > 0 && this.confirmed !== JSON.stringify(form)) {
      this.update({ confirming });
      return;
    }
    this.confirmed = null;
    // Changed while the save runs, or left out of it (not valid yet): keeps what was typed.
    const sent = new Map((Object.keys(form) as (keyof Form)[]).map((field) => [field, this.versions.get(field) ?? 0]));
    const waiting = changedFields(form, ready);
    const keeps = (field: keyof Form) => this.versions.get(field) !== sent.get(field) || waiting.includes(field);
    this.setFields(fields, "saving");
    const result = await config.save(body, base);
    if (result.ok) {
      this.saved(result.data, fields, keeps, stored, ready);
      return;
    }
    await this.failed(result.error, fields);
  }

  private saved(stored: Stored, fields: (keyof Form)[], keeps: (field: keyof Form) => boolean, before: Form, after: Form): void {
    const config = this.config();
    const latest = config.toForm(stored);
    const form = { ...this.snapshot.form };
    for (const field of (Object.keys(latest) as (keyof Form)[]).filter((key) => !keeps(key))) {
      form[field] = latest[field];
    }
    this.retries = 0;
    this.conflictRounds = 0;
    this.update({ base: stored, form, error: null, isReloadFailed: false });
    this.setFields(fields, "saved");
    config.onSaved?.(stored, before, after);
    if (changedFields(form, latest).length > 0 && this.timer === null) {
      this.again = true;
    }
  }

  private async failed(error: ApiError, fields: (keyof Form)[]): Promise<void> {
    const config = this.config();
    if (config.conflict?.isConflict(error) && this.conflictRounds < MAX_CONFLICT_ROUNDS) {
      this.conflictRounds += 1;
      const latest = await config.conflict.reload();
      if (!latest.ok) {
        this.setFields(fields, "failed");
        this.update({ error, isReloadFailed: true });
        return;
      }
      this.rebaseOn(latest.data);
      // What nobody else changed is saved on top of the stored data at once.
      this.again = true;
      return;
    }
    this.setFields(fields, "failed");
    this.update({ error });
    const delays = config.retryDelaysMs ?? DEFAULT_RETRY_DELAYS_MS;
    if (isTransientFailure(error) && this.retries < delays.length && this.timer === null) {
      const delay = delays[this.retries] ?? 0;
      this.retries += 1;
      this.retryTimer = this.clock.setTimeout(() => {
        this.retryTimer = null;
        void this.run();
      }, delay);
    }
  }

  /** Try a failed save again now (the "Try again" of a field). */
  retry(): Promise<void> {
    this.retries = 0;
    return this.flush();
  }
}
