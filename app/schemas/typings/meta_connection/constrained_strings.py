"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class CommentReplyText(BaseConstrainedTypedString):
    """
    The private message an Instagram account sends, once, to a person whose
    comment named one of the owner's keywords (Instagram's private replies
    carry at most 1000 characters).

    Example:
        text = CommentReplyText("Hi! Here is the menu and how to book a table.")
    """

    min_length = 1
    max_length = 1000
    pattern = r"\S"


class CommentTriggerKeyword(BaseConstrainedTypedString):
    """
    A word or short phrase the owner chose: an Instagram comment that holds
    it (in any letter case) gets the private reply. One line, no blank
    edges.

    Example:
        keyword = CommentTriggerKeyword("menu")
    """

    min_length = 1
    max_length = 50
    pattern = r"^\S(?:[^\r\n]*\S)?$"


class MetaCommentId(BaseConstrainedTypedString):
    """
    Meta's id of one comment under an Instagram post (digits; a Facebook
    comment joins the post and comment ids with "_").

    Example:
        comment_id = MetaCommentId("17858893269000001")
    """

    min_length = 1
    max_length = 80
    pattern = r"^[0-9]{1,40}(?:_[0-9]{1,38})?$"


class MetaConfigurationId(BaseConstrainedTypedString):
    """
    The id of a Facebook Login for Business configuration of the platform's
    Meta app: the one of WhatsApp Embedded Signup names the permissions and
    the onboarding flow the owner is shown (META_EMBEDDED_SIGNUP_CONFIG_ID).

    Example:
        config_id = MetaConfigurationId("1234567890123456")
    """

    min_length = 1
    max_length = 32
    pattern = r"^[0-9]{1,32}$"


class MetaConnectionState(BaseConstrainedTypedString):
    """
    The one-time random value that binds a Facebook sign-in in the cabinet
    to the owner and business that started it (URL-safe base64 of 32 bytes).
    Only its hash is stored.

    Example:
        state = MetaConnectionState("q3Jx8m1lV0k7yZcT2b9WnHf4sR6uPaEoLdIgKjQwXeM")
    """

    min_length = 43
    max_length = 43
    pattern = r"^[A-Za-z0-9_-]{43}$"


class MetaConnectionStateHash(BaseConstrainedTypedString):
    """
    SHA-256 (hex) of a `MetaConnectionState`: the key a started connection
    is stored and found under, so the state itself never sits in storage.

    Example:
        state_hash = MetaConnectionStateHash("9f86d0...")  # 64 hex digits
    """

    min_length = 64
    max_length = 64
    pattern = r"^[0-9a-f]{64}$"


class MetaEmbeddedSignupCode(BaseConstrainedTypedString):
    """
    The code WhatsApp Embedded Signup hands the cabinet when the owner
    finishes it: exchanged once, within seconds, for the business's token
    (printable characters only).

    Example:
        code = MetaEmbeddedSignupCode("AQBx7m0Lq2Y3Zr8vT1sNw5kP...")
    """

    min_length = 16
    max_length = 4096
    pattern = r"^[\x21-\x7e]+$"


class MetaGraphApiVersion(BaseConstrainedTypedString):
    """
    The Graph API version the platform speaks and the Facebook SDK loads
    with.

    Example:
        version = MetaGraphApiVersion("v23.0")
    """

    min_length = 4
    max_length = 8
    pattern = r"^v[0-9]{1,3}\.[0-9]{1,2}$"


class MetaLoginCode(BaseConstrainedTypedString):
    """
    The code Facebook Login hands the cabinet when the owner allowed the
    platform to answer for their pages: exchanged once for the owner's
    token, which lists the pages (printable characters only).

    Example:
        code = MetaLoginCode("AQDk2v9Tz0bX7cQm4nRs8wJe...")
    """

    min_length = 16
    max_length = 4096
    pattern = r"^[\x21-\x7e]+$"


class MetaPermissionName(BaseConstrainedTypedString):
    """
    A permission of the Graph API a sign-in asks for or a token holds.

    Example:
        permission = MetaPermissionName("pages_messaging")
    """

    min_length = 2
    max_length = 64
    pattern = r"^[a-z][a-z_]{1,63}$"


class WhatsAppBusinessAccountId(BaseConstrainedTypedString):
    """
    The id of a WhatsApp Business Account (WABA): the account a business's
    numbers, templates and webhooks belong to.

    Example:
        waba_id = WhatsAppBusinessAccountId("102290129340398")
    """

    min_length = 1
    max_length = 32
    pattern = r"^[0-9]{1,32}$"


class WhatsAppRegistrationPin(BaseConstrainedTypedString):
    """
    The six-digit two-step verification PIN a business number is registered
    for the Cloud API with. The platform chooses it and keeps it encrypted,
    so the number can be registered again with the same PIN.

    Example:
        pin = WhatsAppRegistrationPin("482913")
    """

    min_length = 6
    max_length = 6
    pattern = r"^[0-9]{6}$"
