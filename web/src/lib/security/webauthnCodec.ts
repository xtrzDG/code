/**
 * Passkeys between the API and the browser's WebAuthn: the API sends
 * options with binary values as unpadded base64url (snake_case fields),
 * `navigator.credentials` wants ArrayBuffers in WebAuthn dictionaries, and
 * the credential it answers goes back as base64url again. Pure functions:
 * no browser call happens here (see passkeyCeremony.ts).
 */

import type {
  PasskeyCreationOptionsView,
  PasskeyRequestOptionsView,
} from "@/api/types";

/** The credential `POST /v1/me/passkeys` and the enrolment step take. */
export interface RegistrationCredentialJson {
  id: string;
  raw_id: string;
  response: {
    client_data_json: string;
    attestation_object: string;
    transports: string[];
  };
}

/** The credential the sign-in step and step-up take. */
export interface AssertionCredentialJson {
  id: string;
  raw_id: string;
  response: {
    client_data_json: string;
    authenticator_data: string;
    signature: string;
    user_handle: string | null;
  };
}

const TRANSPORT_NAME = /^[a-z][a-z-]{0,31}$/;

/** Unpadded base64url (RFC 4648 §5) of bytes. */
export function toBase64Url(bytes: ArrayBuffer | Uint8Array): string {
  const view = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let binary = "";
  for (const byte of view) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** The bytes of unpadded (or padded) base64url text. */
export function fromBase64Url(text: string): ArrayBuffer {
  const base64 = text.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes.buffer;
}

function descriptors(
  items: readonly { id: string; transports?: readonly string[] }[] | undefined,
): PublicKeyCredentialDescriptor[] {
  return (items ?? []).map((item) => ({
    type: "public-key",
    id: fromBase64Url(item.id),
    transports: (item.transports ?? []) as AuthenticatorTransport[],
  }));
}

/** `PublicKeyCredentialCreationOptions` of a new passkey. */
export function creationOptions(
  view: PasskeyCreationOptionsView,
): PublicKeyCredentialCreationOptions {
  return {
    rp: { id: view.rp.id, name: view.rp.name },
    user: {
      id: fromBase64Url(view.user.id),
      name: view.user.name,
      displayName: view.user.display_name,
    },
    challenge: fromBase64Url(view.challenge),
    pubKeyCredParams: view.algorithms.map((alg) => ({
      type: "public-key",
      alg,
    })),
    timeout: view.timeout_ms,
    excludeCredentials: descriptors(view.exclude_credentials),
    authenticatorSelection: {
      residentKey: view.resident_key,
      userVerification: view.user_verification,
    },
    attestation: "none",
  };
}

/** `PublicKeyCredentialRequestOptions` of a sign-in step or a step-up. */
export function requestOptions(
  view: PasskeyRequestOptionsView,
): PublicKeyCredentialRequestOptions {
  return {
    rpId: view.rp_id,
    challenge: fromBase64Url(view.challenge),
    timeout: view.timeout_ms,
    allowCredentials: descriptors(view.allow_credentials),
    userVerification: view.user_verification,
  };
}

/** The transports a browser reports, kept to well-formed names. */
export function reportedTransports(response: {
  getTransports?: () => string[];
}): string[] {
  const names =
    typeof response.getTransports === "function" ? response.getTransports() : [];
  return names.filter((name) => TRANSPORT_NAME.test(name)).slice(0, 10);
}

/** The API's form of a credential `navigator.credentials.create()` made. */
export function registrationJson(credential: {
  rawId: ArrayBuffer;
  response: {
    clientDataJSON: ArrayBuffer;
    attestationObject: ArrayBuffer;
    getTransports?: () => string[];
  };
}): RegistrationCredentialJson {
  const id = toBase64Url(credential.rawId);
  return {
    id,
    raw_id: id,
    response: {
      client_data_json: toBase64Url(credential.response.clientDataJSON),
      attestation_object: toBase64Url(credential.response.attestationObject),
      transports: reportedTransports(credential.response),
    },
  };
}

/** The API's form of an answer `navigator.credentials.get()` gave. */
export function assertionJson(credential: {
  rawId: ArrayBuffer;
  response: {
    clientDataJSON: ArrayBuffer;
    authenticatorData: ArrayBuffer;
    signature: ArrayBuffer;
    userHandle: ArrayBuffer | null;
  };
}): AssertionCredentialJson {
  const id = toBase64Url(credential.rawId);
  const handle = credential.response.userHandle;
  return {
    id,
    raw_id: id,
    response: {
      client_data_json: toBase64Url(credential.response.clientDataJSON),
      authenticator_data: toBase64Url(credential.response.authenticatorData),
      signature: toBase64Url(credential.response.signature),
      user_handle: handle && handle.byteLength > 0 ? toBase64Url(handle) : null,
    },
  };
}
