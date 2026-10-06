import { describe, expect, it, vi } from "vitest";

import { apiError, engineWith, heldSaves, settled, type Stored, type Values } from "./autosaveFixtures";

const STORED: Stored = { revision: 1, name: "Bistro", days: 90, isOn: true };
const saved = (patch: Partial<Stored>): Stored => ({ ...STORED, ...patch, revision: (patch.revision ?? STORED.revision) + 1 });

describe("AutosaveEngine: when it saves", () => {
  it("waits for typing to stop and sends the last text once", async () => {
    const saves = heldSaves<Partial<Values>, Stored>();
    const { engine, clock } = engineWith(STORED, { save: saves.save });
    engine.change({ name: "Bis" }, 800);
    clock.advance(500);
    engine.change({ name: "Bistro Nova" }, 800);
    clock.advance(799);
    expect(saves.calls).toEqual([]);
    clock.advance(1);
    expect(saves.calls).toEqual([{ name: "Bistro Nova" }]);
    expect(engine.getSnapshot().fields.name?.status).toBe("saving");
    saves.next().settle({ ok: true, data: saved({ name: "Bistro Nova" }) });
    await settled();
    expect(engine.getSnapshot().fields.name).toEqual({ status: "saved", savedAt: clock.now() });
    expect(engine.getSnapshot().isBusy).toBe(false);
  });

  it("runs one save at a time: a change during a save goes in the next one, from the new base", async () => {
    const saves = heldSaves<Partial<Values>, Stored>();
    const { engine } = engineWith(STORED, { save: saves.save });
    engine.change({ isOn: false }, 0);
    const first = engine.flush();
    expect(saves.open()).toBe(1);
    engine.change({ days: 30 }, 0);
    void engine.flush();
    // Held: the first save is still open, so the second has not started.
    expect(saves.open()).toBe(1);
    const open = saves.next();
    open.settle({ ok: true, data: saved({ isOn: false }) });
    await settled();
    expect(saves.calls).toEqual([{ isOn: false }, { days: 30 }]);
    expect(saves.next().base.revision).toBe(2);
    await expect(Promise.race([first, Promise.resolve("open")])).resolves.toBe("open");
  });

  it("keeps what was typed during a save and shows the server's value of the rest", async () => {
    const saves = heldSaves<Partial<Values>, Stored>();
    const { engine } = engineWith(STORED, { save: saves.save });
    engine.change({ name: "  Nova " }, 0);
    void engine.flush();
    engine.change({ days: 365 }, 10_000);
    saves.next().settle({ ok: true, data: saved({ name: "Nova" }) });
    await settled();
    expect(engine.getSnapshot().form).toEqual({ name: "Nova", days: 365, isOn: true });
  });

  it("lets a field that is not valid yet wait with its stored value", async () => {
    const saves = heldSaves<Partial<Values>, Stored>();
    const { engine } = engineWith(STORED, { save: saves.save, invalidFields: (form) => (form.name.trim() === "" ? ["name"] : []) });
    engine.change({ name: "", isOn: false }, 0);
    void engine.flush();
    expect(saves.calls).toEqual([{ isOn: false }]);
    saves.next().settle({ ok: true, data: saved({ isOn: false }) });
    await settled();
    expect(engine.getSnapshot().form.name).toBe("");
    expect(saves.open()).toBe(0);
  });

  it("sends nothing for a change put back before the save", async () => {
    const save = vi.fn();
    const { engine } = engineWith(STORED, { save });
    engine.change({ days: 30 }, 800);
    engine.change({ days: 90 }, 800);
    await engine.flush();
    expect(save).not.toHaveBeenCalled();
  });
});

describe("AutosaveEngine: when a save fails", () => {
  it("tries again by itself after a lost connection, then gives up and waits for Try again", async () => {
    const saves = heldSaves<Partial<Values>, Stored>();
    const { engine, clock } = engineWith(STORED, { save: saves.save, retryDelaysMs: [1_000] });
    engine.change({ days: 30 }, 0);
    void engine.flush();
    saves.next().settle({ ok: false, error: apiError("network_error", 0) });
    await settled();
    expect(engine.getSnapshot().fields.days?.status).toBe("failed");
    expect(engine.getSnapshot().isBusy).toBe(true);
    clock.advance(1_000);
    expect(saves.open()).toBe(1);
    saves.next().settle({ ok: false, error: apiError("backend_unavailable", 503) });
    await settled();
    expect(clock.pending()).toBe(0);
    void engine.retry();
    saves.next().settle({ ok: true, data: saved({ days: 30 }) });
    await settled();
    expect(engine.getSnapshot().fields.days?.status).toBe("saved");
    expect(engine.getSnapshot().error).toBeNull();
  });

  it("does not retry a refusal; the error stays until a save goes through", async () => {
    const saves = heldSaves<Partial<Values>, Stored>();
    const { engine, clock } = engineWith(STORED, { save: saves.save });
    engine.change({ name: "x" }, 0);
    void engine.flush();
    saves.next().settle({ ok: false, error: apiError("validation_failed", 422) });
    await settled();
    expect(engine.getSnapshot().error?.code).toBe("validation_failed");
    expect(clock.pending()).toBe(0);
  });

  it("puts a save refused as stale on top of what is stored and saves what nobody else changed", async () => {
    const saves = heldSaves<Partial<Values>, Stored>();
    const latest: Stored = { revision: 5, name: "Hamburg", days: 90, isOn: true };
    const { engine } = engineWith(STORED, {
      save: saves.save,
      conflict: {
        isConflict: (error) => error.status === 409,
        reload: async () => ({ ok: true, data: latest }),
        rebase: (shown, stored, form) => ({
          form: { ...form, name: stored.name !== shown.name ? stored.name : form.name },
          conflicts: stored.name !== shown.name && form.name !== shown.name ? ["name"] : [],
        }),
      },
    });
    engine.change({ name: "Potsdam", days: 30 }, 0);
    void engine.flush();
    saves.next().settle({ ok: false, error: apiError("conflict", 409, "stale_revision") });
    await settled();
    const retried = saves.next();
    expect(retried.body).toEqual({ days: 30 });
    expect(retried.base.revision).toBe(5);
    expect(engine.getSnapshot().conflicts).toEqual(["name"]);
    expect(engine.getSnapshot().form.name).toBe("Hamburg");
    retried.settle({ ok: true, data: { ...latest, days: 30, revision: 6 } });
    await settled();
    expect(engine.getSnapshot().fields.days?.status).toBe("saved");
  });

  it("says so when what is stored cannot be loaded after a stale refusal, and loads it and saves the rest on request", async () => {
    const saves = heldSaves<Partial<Values>, Stored>();
    const reload = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, error: apiError("backend_unavailable", 503) })
      .mockResolvedValueOnce({ ok: true, data: { ...STORED, revision: 3, name: "Hamburg" } });
    const { engine } = engineWith(STORED, {
      save: saves.save,
      conflict: { isConflict: () => true, reload, rebase: (_shown, stored, form) => ({ form: { ...form, name: stored.name }, conflicts: ["name"] }) },
    });
    engine.change({ name: "Potsdam", days: 30 }, 0);
    void engine.flush();
    saves.next().settle({ ok: false, error: apiError("conflict", 409) });
    await settled();
    expect(engine.getSnapshot().isReloadFailed).toBe(true);
    expect(engine.getSnapshot().form.name).toBe("Potsdam");
    expect(engine.getSnapshot().fields.days?.status).toBe("failed");
    const reloading = engine.reloadStored();
    await settled();
    expect(engine.getSnapshot()).toMatchObject({ isReloadFailed: false, conflicts: ["name"], form: { name: "Hamburg", days: 30 } });
    const rest = saves.next();
    expect([rest.body, rest.base.revision]).toEqual([{ days: 30 }, 3]);
    rest.settle({ ok: true, data: { ...STORED, revision: 4, name: "Hamburg", days: 30 } });
    await expect(reloading).resolves.toBe(true);
    expect(engine.getSnapshot().fields.days?.status).toBe("saved");
  });
});

describe("AutosaveEngine: confirmations, undo and copies from elsewhere", () => {
  it("asks before a change that deletes data, saves it once confirmed, and puts it back when not", async () => {
    const saves = heldSaves<Partial<Values>, Stored>();
    const { engine } = engineWith(STORED, {
      save: saves.save,
      needsConfirmation: (form, base) => (form.days < base.days ? ["days"] : []),
    });
    engine.change({ days: 30 }, 0);
    await engine.flush();
    expect(engine.getSnapshot().confirming).toEqual(["days"]);
    expect(saves.calls).toEqual([]);
    engine.cancelConfirmation();
    expect(engine.getSnapshot().form.days).toBe(90);
    engine.change({ days: 30 }, 0);
    await engine.flush();
    void engine.confirm();
    expect(saves.calls).toEqual([{ days: 30 }]);
  });

  it("tells who saved what and puts a change back on Undo", async () => {
    const saves = heldSaves<Partial<Values>, Stored>();
    const onSaved = vi.fn();
    const { engine, clock } = engineWith(STORED, { save: saves.save, onSaved });
    engine.change({ isOn: false }, 0);
    void engine.flush();
    saves.next().settle({ ok: true, data: saved({ isOn: false }) });
    await settled();
    const [, before, after] = onSaved.mock.calls[0] as [Stored, Values, Values];
    expect([before.isOn, after.isOn]).toEqual([true, false]);
    engine.revert(before, after);
    clock.advance(0);
    await settled();
    expect(saves.calls.at(-1)).toEqual({ isOn: true });
  });

  it("takes a newer copy from elsewhere while idle, and only its revision while saving", async () => {
    const saves = heldSaves<Partial<Values>, Stored>();
    const { engine } = engineWith(STORED, { save: saves.save, isNewer: (candidate, base) => candidate.revision > base.revision });
    engine.adopt({ ...STORED, revision: 0, name: "Old" });
    expect(engine.getSnapshot().form.name).toBe("Bistro");
    engine.adopt({ ...STORED, revision: 2, name: "Elsewhere" });
    expect(engine.getSnapshot().form.name).toBe("Elsewhere");
    engine.change({ days: 30 }, 5_000);
    engine.adopt({ ...STORED, revision: 3, name: "Elsewhere" });
    expect(engine.getSnapshot().base.revision).toBe(3);
    engine.adopt({ ...STORED, revision: 4, name: "Third" });
    expect(engine.getSnapshot().base.revision).toBe(3);
    expect(engine.getSnapshot().form).toEqual({ name: "Elsewhere", days: 30, isOn: true });
  });
});
