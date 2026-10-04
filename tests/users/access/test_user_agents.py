"""The browser, system and kind of device a User-Agent names."""

import pytest

from app.schemas.constants.users import SessionDeviceKind
from app.utilities.security.user_agents import (
    describe_device,
    is_same_device,
    names_a_device,
    read_user_agent,
)
from tests.users.access.session_steps import (
    ANDROID_CHROME,
    IPHONE_SAFARI,
    MAC_CHROME,
)

WINDOWS_EDGE: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like "
    "Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.2903.70"
)
LINUX_FIREFOX: str = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0"
)
IPAD_SAFARI: str = (
    "Mozilla/5.0 (iPad; CPU OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, "
    "like Gecko) Version/17.6 Mobile/15E148 Safari/604.1"
)
ANDROID_TABLET: str = (
    "Mozilla/5.0 (Linux; Android 14; SM-X710) AppleWebKit/537.36 (KHTML, like "
    "Gecko) SamsungBrowser/26.0 Chrome/122.0.0.0 Safari/537.36"
)
YANDEX_WINDOWS: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like "
    "Gecko) Chrome/130.0.0.0 YaBrowser/24.12.0.0 Safari/537.36"
)
OPERA_MAC: str = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, "
    "like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.0"
)
CHROMEBOOK: str = (
    "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 (KHTML, like "
    "Gecko) Chrome/131.0.0.0 Safari/537.36"
)


@pytest.mark.parametrize(
    ("user_agent", "browser", "system", "kind"),
    [
        (MAC_CHROME, "Chrome", "macOS", SessionDeviceKind.DESKTOP),
        (IPHONE_SAFARI, "Safari", "iOS", SessionDeviceKind.PHONE),
        (ANDROID_CHROME, "Chrome", "Android", SessionDeviceKind.PHONE),
        (WINDOWS_EDGE, "Edge", "Windows", SessionDeviceKind.DESKTOP),
        (LINUX_FIREFOX, "Firefox", "Linux", SessionDeviceKind.DESKTOP),
        (IPAD_SAFARI, "Safari", "iPadOS", SessionDeviceKind.TABLET),
        (
            ANDROID_TABLET,
            "Samsung Internet",
            "Android",
            SessionDeviceKind.TABLET,
        ),
        (YANDEX_WINDOWS, "Yandex Browser", "Windows", SessionDeviceKind.DESKTOP),
        (OPERA_MAC, "Opera", "macOS", SessionDeviceKind.DESKTOP),
        (CHROMEBOOK, "Chrome", "ChromeOS", SessionDeviceKind.DESKTOP),
    ],
)
def test_browsers_and_systems_are_named(
    user_agent: str, browser: str, system: str, kind: SessionDeviceKind
) -> None:
    device = describe_device(read_user_agent(user_agent))

    assert (device.browser, device.operating_system, device.kind) == (
        browser,
        system,
        kind,
    )


def test_unknown_and_missing_user_agents() -> None:
    assert describe_device(None).kind is SessionDeviceKind.UNKNOWN
    assert describe_device(read_user_agent("curl/8.9.1")).browser is None
    assert names_a_device(read_user_agent("node")) is False
    assert names_a_device(read_user_agent(MAC_CHROME)) is True


def test_user_agents_are_kept_printable_and_short() -> None:
    assert read_user_agent(None) is None
    assert read_user_agent(" \t\n ") is None
    assert str(read_user_agent("Mozilla/5.0\x00 (X11)\n")) == "Mozilla/5.0 (X11)"
    long_agent = read_user_agent("A" * 2000)
    assert long_agent is not None and len(str(long_agent)) == 512


def test_the_same_device_is_the_same_browser_on_the_same_system() -> None:
    newer_chrome = MAC_CHROME.replace("131.0.0.0", "132.0.0.0")

    assert is_same_device(
        describe_device(read_user_agent(MAC_CHROME)),
        describe_device(read_user_agent(newer_chrome)),
    )
    assert not is_same_device(
        describe_device(read_user_agent(MAC_CHROME)),
        describe_device(read_user_agent(OPERA_MAC)),
    )
    assert not is_same_device(describe_device(None), describe_device(None))
