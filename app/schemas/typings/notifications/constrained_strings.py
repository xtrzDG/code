"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class CabinetDeepLink(BaseConstrainedTypedString):
    """
    Address of a cabinet page that a staff notification opens: the
    cabinet's public address and a signed, expiring link path.

    Example:
        link = CabinetDeepLink("https://app.example.com/n/AQ3x...")
    """

    min_length = 10
    max_length = 512
    pattern = r"^https?://[^\s/]+/n/[A-Za-z0-9_-]+$"


class PushAuthSecret(BaseConstrainedTypedString):
    """
    The authentication secret a browser gives with its push subscription
    (16 bytes, base64url), used to encrypt messages for it (RFC 8291).

    Example:
        secret = PushAuthSecret("BTBZMqHH6r4Tts7J_aSIgg")
    """

    min_length = 16
    max_length = 64
    pattern = r"^[A-Za-z0-9_-]+={0,2}$"


class PushEndpointUrl(BaseConstrainedTypedString):
    """
    The push service address of one browser subscription (Mozilla, Google,
    Apple...), where encrypted messages are posted.

    Example:
        endpoint = PushEndpointUrl("https://fcm.googleapis.com/fcm/send/c1...")
    """

    min_length = 12
    max_length = 2048
    pattern = r"^https://[^\s]+$"


class PushNotificationTag(BaseConstrainedTypedString):
    """
    The tag of a device notification: a newer one with the same tag
    replaces the older (one notification per handoff, lead or booking).

    Example:
        tag = PushNotificationTag("handoff:handoff_6f1b8f52-2c55-...")
    """

    min_length = 1
    max_length = 120
    pattern = r"^[a-z_]+:[A-Za-z0-9_:-]+$"


class PushPublicKey(BaseConstrainedTypedString):
    """
    The browser's P-256 public key of a push subscription (`p256dh`, an
    uncompressed point, base64url).

    Example:
        key = PushPublicKey("BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcx...")
    """

    min_length = 80
    max_length = 100
    pattern = r"^[A-Za-z0-9_-]+={0,2}$"


class StaffLinkToken(BaseConstrainedTypedString):
    """
    The signed, expiring token of a notification link: which page of which
    business it opens and until when (base64url, no padding).

    Example:
        token = StaffLinkToken("AQ3xL8...")
    """

    min_length = 40
    max_length = 120
    pattern = r"^[A-Za-z0-9_-]+$"


class VapidPublicKey(BaseConstrainedTypedString):
    """
    The platform's public Web Push (VAPID) key, an uncompressed P-256 point
    in base64url: browsers subscribe with it.

    Example:
        key = VapidPublicKey("BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMo...")
    """

    min_length = 86
    max_length = 88
    pattern = r"^[A-Za-z0-9_-]+={0,2}$"


class VapidSubject(BaseConstrainedTypedString):
    """
    Who push services contact about the platform's messages (RFC 8292): a
    mailto: address or an https: page.

    Example:
        subject = VapidSubject("mailto:ops@example.com")
    """

    min_length = 8
    max_length = 320
    pattern = r"^(mailto:[^\s@]+@[^\s@]+|https://[^\s]+)$"


# Keep abc order for all non example types, if possible.
