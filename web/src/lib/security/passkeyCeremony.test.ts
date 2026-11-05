import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/errors";
import type { PasskeyCreationOptionsView, PasskeyRequestOptionsView } from "@/api/types";

import {
  canUsePasskeys,
  createPasskey,
  PasskeyCeremonyError,
  signWithPasskey,
} from "./passkeyCeremony";
import { passkeyApiProblem, passkeyProblem } from "./passkeyProblem";
import { toBase64Url } from "./webauthnCodec";

const ID = toBase64Url(new TextEncoder().encode("key-1"));

const CREATION: PasskeyCreationOptionsView = {
  rp: { id: "localhost", name: "Assistant Workshop" },
  user: { id: ID, name: "owner@example.com", display_name: "Owner" },
  challenge: ID,
  algorithms: [-7],
  timeout_ms: 60_000,
  resident_key: "preferred",
  user_verification: "preferred",
};

const REQUEST: PasskeyRequestOptionsView = {
  rp_id: "localhost",
  challenge: ID,
  timeout_ms: 60_000,
  user_verification: "preferred",
};

/** A browser whose authenticator answers (or refuses) with `answer`. */
function browserWith(answer: () => Promise<unknown>) {
  class FakePublicKeyCredential {
    rawId = new TextEncoder().encode("key-1").buffer;
    response = {
      clientDataJSON: new ArrayBuffer(2),
      attestationObject: new ArrayBuffer(3),
      authenticatorData: new ArrayBuffer(4),
      signature: new ArrayBuffer(5),
      userHandle: null,
      getTransports: () => ["internal"],
    };
  }
  vi.stubGlobal("PublicKeyCredential", FakePublicKeyCredential);
  vi.stubGlobal("navigator", {
    credentials: {
      create: vi.fn(async () => {
        const value = await answer();
        return value === "credential" ? new FakePublicKeyCredential() : value;
      }),
      get: vi.fn(async () => {
        const value = await answer();
        return value === "credential" ? new FakePublicKeyCredential() : value;
      }),
    },
  });
}

function refusedWith(name: string) {
  return () => Promise.reject(Object.assign(new Error(name), { name }));
}

function refusal(reason: string): ApiError {
  return new ApiError({
    status: reason === "passkeys_unavailable" ? 409 : 422,
    code: reason === "passkeys_unavailable" ? "conflict" : "validation_failed",
    reasons: [{ code: reason, message: "", details: [] }],
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the passkey ceremony", () => {
  it("is offered only where the browser has WebAuthn", () => {
    vi.stubGlobal("PublicKeyCredential", undefined);
    expect(canUsePasskeys()).toBe(false);
    browserWith(async () => "credential");
    expect(canUsePasskeys()).toBe(true);
  });

  it("answers in the API's form", async () => {
    browserWith(async () => "credential");

    const created = await createPasskey(CREATION);
    const signed = await signWithPasskey(REQUEST);

    expect(created.id).toBe(ID);
    expect(created.response.transports).toEqual(["internal"]);
    expect(signed.raw_id).toBe(ID);
    expect(signed.response.user_handle).toBeNull();
  });

  it.each([
    ["NotAllowedError", "passkeys.errors.cancelled"],
    ["AbortError", "passkeys.errors.cancelled"],
    ["InvalidStateError", "passkeys.errors.alreadyAdded"],
    ["SecurityError", "passkeys.errors.wrongSite"],
    ["UnknownError", "passkeys.errors.unsupported"],
  ])("tells a %s as %s", async (name, key) => {
    browserWith(refusedWith(name));

    await expect(createPasskey(CREATION)).rejects.toMatchObject({ messageKey: key });
    await expect(signWithPasskey(REQUEST)).rejects.toMatchObject({ messageKey: key });
  });

  it("takes no answer as cancelled", async () => {
    browserWith(async () => null);

    await expect(signWithPasskey(REQUEST)).rejects.toBeInstanceOf(PasskeyCeremonyError);
  });

  it("refuses at once without WebAuthn", async () => {
    vi.stubGlobal("PublicKeyCredential", undefined);

    await expect(createPasskey(CREATION)).rejects.toMatchObject({ messageKey: "passkeys.errors.unsupported" });
  });
});

describe("what the person is told", () => {
  it("names the API's passkey refusals", () => {
    expect(passkeyApiProblem(refusal("passkey_clone_suspected"))).toBe("passkeys.errors.suspended");
    expect(passkeyApiProblem(refusal("passkey_rejected"))).toBe("passkeys.errors.rejected");
    expect(passkeyApiProblem(refusal("passkeys_unavailable"))).toBe("passkeys.errors.unavailable");
  });

  it("prefers the ceremony's own reason", () => {
    const caught = new PasskeyCeremonyError("passkeys.errors.cancelled");
    expect(passkeyProblem(caught, refusal("passkey_rejected"))).toBe("passkeys.errors.cancelled");
  });

  it("leaves other failures to a toast", () => {
    expect(passkeyApiProblem(new ApiError({ status: 500, code: "internal_error" }))).toBeNull();
  });
});
