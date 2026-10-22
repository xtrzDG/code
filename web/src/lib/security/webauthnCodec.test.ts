import { describe, expect, it } from "vitest";

import type {
  PasskeyCreationOptionsView,
  PasskeyRequestOptionsView,
} from "@/api/types";

import {
  assertionJson,
  creationOptions,
  fromBase64Url,
  registrationJson,
  reportedTransports,
  requestOptions,
  toBase64Url,
} from "./webauthnCodec";

function bytes(text: string): ArrayBuffer {
  return new TextEncoder().encode(text).buffer as ArrayBuffer;
}

function text(buffer: ArrayBuffer | BufferSource | undefined): string {
  return new TextDecoder().decode(buffer as ArrayBuffer);
}

const CREATION: PasskeyCreationOptionsView = {
  rp: { id: "cabinet.example.com", name: "Assistant Workshop" },
  user: { id: toBase64Url(bytes("user_1")), name: "owner@example.com", display_name: "Owner" },
  challenge: toBase64Url(bytes("challenge-0000")),
  algorithms: [-7, -257],
  timeout_ms: 60_000,
  exclude_credentials: [{ id: toBase64Url(bytes("old-key")), transports: ["internal", "hybrid"] }],
  resident_key: "preferred",
  user_verification: "preferred",
};

const REQUEST: PasskeyRequestOptionsView = {
  rp_id: "cabinet.example.com",
  challenge: toBase64Url(bytes("sign-0000")),
  timeout_ms: 60_000,
  allow_credentials: [{ id: toBase64Url(bytes("key-1")) }],
  user_verification: "preferred",
};

describe("base64url", () => {
  it("writes bytes without padding and with the URL alphabet", () => {
    const encoded = toBase64Url(new Uint8Array([251, 255, 191, 0]));
    expect(encoded).toBe("-_-_AA");
    expect(new Uint8Array(fromBase64Url(encoded))).toEqual(new Uint8Array([251, 255, 191, 0]));
  });

  it("reads padded text as well", () => {
    expect(text(fromBase64Url("aGk="))).toBe("hi");
    expect(text(fromBase64Url("aGk"))).toBe("hi");
  });
});

describe("options for the browser", () => {
  it("turns a new passkey's options into WebAuthn's dictionary", () => {
    const options = creationOptions(CREATION);

    expect(options.rp).toEqual({ id: "cabinet.example.com", name: "Assistant Workshop" });
    expect(text(options.user.id)).toBe("user_1");
    expect(options.user).toMatchObject({ name: "owner@example.com", displayName: "Owner" });
    expect(text(options.challenge)).toBe("challenge-0000");
    expect(options.pubKeyCredParams).toEqual([
      { type: "public-key", alg: -7 },
      { type: "public-key", alg: -257 },
    ]);
    expect(options.excludeCredentials?.map((item) => text(item.id))).toEqual(["old-key"]);
    expect(options.excludeCredentials?.[0]?.transports).toEqual(["internal", "hybrid"]);
    expect(options.authenticatorSelection).toEqual({ residentKey: "preferred", userVerification: "preferred" });
    expect(options.attestation).toBe("none");
  });

  it("turns a sign-in step's options into WebAuthn's dictionary", () => {
    const options = requestOptions(REQUEST);

    expect(options.rpId).toBe("cabinet.example.com");
    expect(text(options.challenge)).toBe("sign-0000");
    expect(options.allowCredentials?.map((item) => text(item.id))).toEqual(["key-1"]);
    expect(options.allowCredentials?.[0]?.transports).toEqual([]);
    expect(options.timeout).toBe(60_000);
  });

  it("allows any passkey of the person when the API lists none", () => {
    expect(requestOptions({ ...REQUEST, allow_credentials: undefined }).allowCredentials).toEqual([]);
  });
});

describe("answers for the API", () => {
  it("keeps only well-formed transport names", () => {
    expect(reportedTransports({ getTransports: () => ["internal", "hybrid", "Bad Name", "<script>"] })).toEqual([
      "internal",
      "hybrid",
    ]);
    expect(reportedTransports({})).toEqual([]);
  });

  it("writes a new passkey as base64url", () => {
    const json = registrationJson({
      rawId: bytes("key-1"),
      response: {
        clientDataJSON: bytes("{}"),
        attestationObject: bytes("attestation"),
        getTransports: () => ["internal"],
      },
    });

    expect(json).toEqual({
      id: toBase64Url(bytes("key-1")),
      raw_id: toBase64Url(bytes("key-1")),
      response: {
        client_data_json: toBase64Url(bytes("{}")),
        attestation_object: toBase64Url(bytes("attestation")),
        transports: ["internal"],
      },
    });
  });

  it("writes a signed answer, without an empty user handle", () => {
    const answer = {
      rawId: bytes("key-1"),
      response: {
        clientDataJSON: bytes("{}"),
        authenticatorData: bytes("data"),
        signature: bytes("signature"),
        userHandle: bytes("user_1"),
      },
    };

    expect(assertionJson(answer).response).toEqual({
      client_data_json: toBase64Url(bytes("{}")),
      authenticator_data: toBase64Url(bytes("data")),
      signature: toBase64Url(bytes("signature")),
      user_handle: toBase64Url(bytes("user_1")),
    });
    expect(assertionJson({ ...answer, response: { ...answer.response, userHandle: new ArrayBuffer(0) } }).response.user_handle).toBeNull();
    expect(assertionJson({ ...answer, response: { ...answer.response, userHandle: null } }).response.user_handle).toBeNull();
  });
});
