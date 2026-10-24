"""Keep abc order."""

from base_typed_string import BaseTypedString


class MetaAccessToken(BaseTypedString):
    """
    A token Meta issued for a code the cabinet handed over: the business's
    token of WhatsApp Embedded Signup, or the owner's own token of Facebook
    Login (it lists the pages they manage). Never logged, never returned to
    a browser; a business's token is stored only encrypted, as its channel
    credential.
    """


class MetaPageAccessToken(BaseTypedString):
    """
    The token of one Facebook page, read with the owner's token: the page's
    Messenger and Instagram messages are sent with it. Never logged; stored
    only encrypted, as the channel credential.
    """
