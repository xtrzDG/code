from enum import StrEnum


class PasskeyCeremonyPurpose(StrEnum):
    """
    What one passkey challenge is for: adding a passkey to the signed-in
    person's account (REGISTRATION), adding one while a platform admin
    without a second factor signs in (SIGN_IN_ENROLLMENT), the second step
    of a sign-in (SIGN_IN), or confirming it is them before a sensitive
    action (STEP_UP). A challenge answers only its own purpose.
    """

    REGISTRATION = "registration"
    SIGN_IN_ENROLLMENT = "sign_in_enrollment"
    SIGN_IN = "sign_in"
    STEP_UP = "step_up"


class SecondFactorMethod(StrEnum):
    """
    A way to pass the second step of a sign-in: a passkey (phishing
    resistant, offered first), a code of the authenticator app, or one of
    the recovery codes.
    """

    PASSKEY = "passkey"
    TOTP = "totp"
    RECOVERY_CODE = "recovery_code"


class WebAuthnTransport(StrEnum):
    """
    How a browser reaches the authenticator that keeps a passkey (WebAuthn
    `AuthenticatorTransport`), remembered so the browser offers the right
    one next time.
    """

    USB = "usb"
    NFC = "nfc"
    BLE = "ble"
    SMART_CARD = "smart-card"
    HYBRID = "hybrid"
    INTERNAL = "internal"
    CABLE = "cable"


class WebAuthnResidentKey(StrEnum):
    """
    Whether the authenticator should keep the passkey discoverable (a
    passkey the browser can list) or may keep a server-side credential.
    """

    REQUIRED = "required"
    PREFERRED = "preferred"
    DISCOURAGED = "discouraged"


class WebAuthnUserVerification(StrEnum):
    """
    Whether the authenticator checks the person (fingerprint, face, PIN)
    before it signs.
    """

    REQUIRED = "required"
    PREFERRED = "preferred"
    DISCOURAGED = "discouraged"
