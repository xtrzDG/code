import { describe, expect, it } from "vitest";

import {
  emptyResourceForm,
  resourceCreateBody,
  resourceFormFromView,
  resourcePatchBody,
  sortResources,
  validateResourceForm,
  type ResourceView,
} from "./resources";

const resource = (patch: Partial<ResourceView> = {}): ResourceView => ({
  id: "resource_1",
  business_id: "business_1",
  kind: "table",
  name: "Window table",
  capacity: 4,
  unit_count: 3,
  booking_unit: "time_slot",
  slot_minutes: null,
  schedule: [],
  is_active: true,
  created_at: 0,
  updated_at: 0,
  ...patch,
});

describe("resources", () => {
  it("validates names and whole numbers in range", () => {
    const form = emptyResourceForm("table", "time_slot");
    expect(validateResourceForm(form)).toEqual({ name: "validation.required", capacity: "validation.required" });
    expect(validateResourceForm({ ...form, name: "A", capacity: "4", units: "0" })).toEqual({ units: "validation.positive" });
    expect(validateResourceForm({ ...form, name: "A", capacity: "4.5" })).toEqual({ capacity: "validation.wholeNumber" });
    expect(validateResourceForm({ ...form, name: "A", capacity: "20000" })).toEqual({ capacity: "knowledge.resources.errors.tooLarge" });
    expect(validateResourceForm({ ...form, name: "A", capacity: "4", slotMinutes: "3" })).toEqual({
      slotMinutes: "knowledge.resources.errors.slotTooShort",
    });
    expect(validateResourceForm({ ...form, name: "A", capacity: "4", slotMinutes: "" })).toEqual({});
  });

  it("builds the create body; without its own hours a resource follows the business", () => {
    const form = { ...emptyResourceForm("arena", "time_slot"), name: " Arena 1 ", capacity: "8", slotMinutes: "60" };
    const schedule = [{ weekday: 1 as const, opens_at: 600, closes_at: 1200 }];
    expect(resourceCreateBody(form, schedule)).toEqual({
      name: "Arena 1",
      kind: "arena",
      capacity: 8,
      unit_count: 1,
      slot_minutes: 60,
      booking_unit: "time_slot",
      is_active: true,
      schedule: [],
      serves_item_ids: [],
      room_type_item_id: null,
    });
    expect(resourceCreateBody({ ...form, hasOwnSchedule: true }, schedule).schedule).toEqual(schedule);
  });

  it("links a resource booked by time to services and a room booked by the night to its type", () => {
    const form = { ...emptyResourceForm("staff", "time_slot"), name: "Nino", capacity: "1", serviceIds: ["cut", "cut", "color"], roomTypeId: "deluxe" };
    expect(resourceCreateBody(form, [])).toMatchObject({ serves_item_ids: ["cut", "color"], room_type_item_id: null });
    const room = { ...form, kind: "room" as const, bookingUnit: "night" as const };
    expect(resourceCreateBody(room, [])).toMatchObject({ serves_item_ids: [], room_type_item_id: "deluxe" });
    expect(resourceCreateBody({ ...room, roomTypeId: "" }, []).room_type_item_id).toBeNull();

    const view = resource({ kind: "staff", serves_item_ids: ["cut"], room_type_item_id: null });
    const edit = resourceFormFromView(view);
    expect(edit).toMatchObject({ serviceIds: ["cut"], roomTypeId: "" });
    expect(resourcePatchBody({ ...edit, serviceIds: ["color", "cut"] }, view, [])).toEqual({ serves_item_ids: ["color", "cut"] });
    expect(resourcePatchBody({ ...edit, serviceIds: [] }, view, [])).toEqual({ serves_item_ids: [] });
    const roomView = resource({ kind: "room", booking_unit: "night", room_type_item_id: "deluxe" });
    expect(resourcePatchBody({ ...resourceFormFromView(roomView), roomTypeId: "" }, roomView, [])).toEqual({ room_type_item_id: null });
  });

  it("patches only what changed", () => {
    const view = resource({ schedule: [{ weekday: 2, opens_at: 600, closes_at: 1200 }] });
    const form = resourceFormFromView(view);
    expect(form.hasOwnSchedule).toBe(true);
    expect(resourcePatchBody(form, view, view.schedule ?? [])).toEqual({});
    expect(resourcePatchBody({ ...form, capacity: "6", isActive: false }, view, view.schedule ?? [])).toEqual({
      capacity: 6,
      is_active: false,
    });
    expect(resourcePatchBody({ ...form, hasOwnSchedule: false }, view, view.schedule ?? [])).toEqual({ schedule: [] });
    expect(resourcePatchBody({ ...form, slotMinutes: "90" }, view, view.schedule ?? [])).toEqual({ slot_minutes: 90 });
  });

  it("lists active resources first, by name", () => {
    const sorted = sortResources(
      [resource({ id: "b", name: "B" }), resource({ id: "off", name: "A", is_active: false }), resource({ id: "a", name: "A" })],
      "en",
    );
    expect(sorted.map((item) => item.id)).toEqual(["a", "b", "off"]);
  });
});
