"""
The browser, system and kind of device a User-Agent names, for the
sessions list and the new-device check. A few ordered rules cover the
browsers people use; anything else reads as an unknown device.
"""

import re

from app.schemas.constants.users import SessionDeviceKind
from app.schemas.dto.sessions import SessionDevice
from app.schemas.typings.users.constrained_strings import SessionUserAgent
from app.schemas.typings.users.strings import (
    SessionBrowserName,
    SessionOperatingSystem,
)

# Order matters: Edge, Opera, Yandex and Samsung also say "Chrome", and
# Chrome also says "Safari".
BROWSER_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bEdg(e|A|iOS)?/"), "Edge"),
    (re.compile(r"\b(OPR|Opera|OPX)/"), "Opera"),
    (re.compile(r"\bYaBrowser/"), "Yandex Browser"),
    (re.compile(r"\bSamsungBrowser/"), "Samsung Internet"),
    (re.compile(r"\b(Firefox|FxiOS)/"), "Firefox"),
    (re.compile(r"\b(CriOS|Chrome|Chromium|HeadlessChrome)/"), "Chrome"),
    (re.compile(r"\bVersion/[\d.]+.*\bSafari/"), "Safari"),
)
SYSTEM_RULES: tuple[tuple[re.Pattern[str], str, SessionDeviceKind], ...] = (
    (re.compile(r"\biPad\b"), "iPadOS", SessionDeviceKind.TABLET),
    (re.compile(r"\b(iPhone|iPod)\b"), "iOS", SessionDeviceKind.PHONE),
    (re.compile(r"\bAndroid\b.*\bMobile\b"), "Android", SessionDeviceKind.PHONE),
    (re.compile(r"\bAndroid\b"), "Android", SessionDeviceKind.TABLET),
    (re.compile(r"\bWindows\b"), "Windows", SessionDeviceKind.DESKTOP),
    (re.compile(r"\bCrOS\b"), "ChromeOS", SessionDeviceKind.DESKTOP),
    (re.compile(r"\b(Macintosh|Mac OS X)\b"), "macOS", SessionDeviceKind.DESKTOP),
    (re.compile(r"\bLinux\b"), "Linux", SessionDeviceKind.DESKTOP),
)


def describe_device(user_agent: SessionUserAgent | None) -> SessionDevice:
    """What the User-Agent says (an unknown device when it says nothing)."""

    if user_agent is None:
        return SessionDevice()

    text: str = str(user_agent)
    browser: str | None = next(
        (name for pattern, name in BROWSER_RULES if pattern.search(text)), None
    )
    system: tuple[str, SessionDeviceKind] | None = next(
        ((name, kind) for pattern, name, kind in SYSTEM_RULES if pattern.search(text)),
        None,
    )
    return SessionDevice(
        kind=system[1] if system is not None else SessionDeviceKind.UNKNOWN,
        browser=SessionBrowserName(browser) if browser is not None else None,
        operating_system=(
            SessionOperatingSystem(system[0]) if system is not None else None
        ),
    )


def names_a_device(user_agent: SessionUserAgent | None) -> bool:
    """
    The User-Agent names a browser or a system (a server-side HTTP client
    such as "node" names neither, and never replaces a stored one).
    """

    device: SessionDevice = describe_device(user_agent)
    return device.browser is not None or device.operating_system is not None


def is_same_device(first: SessionDevice, second: SessionDevice) -> bool:
    """
    The same browser on the same system (versions aside): a sign-in from
    it is not news. Two unknown devices are never the same.
    """

    if first.browser is None and first.operating_system is None:
        return False

    return (
        first.browser == second.browser
        and first.operating_system == second.operating_system
        and first.kind is second.kind
    )


def read_user_agent(raw_value: str | None) -> SessionUserAgent | None:
    """
    The User-Agent header as stored: printable ASCII only, cut to 512
    characters; None when nothing printable is left.
    """

    if raw_value is None:
        return None

    printable: str = (
        "".join(character for character in raw_value if " " <= character <= "~")
        .strip()[:512]
        .strip()
    )
    return SessionUserAgent(printable) if printable else None
