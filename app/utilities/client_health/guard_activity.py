"""
When the reply guard's work is a pattern worth a look (GUARD_SPIKE): the
guard held back at least one reply in six over at least five held-back
replies (the facts are thin or the model invents), or at least ten
customer messages of the window looked like prompt injection (someone is
probing the assistant).
"""

from app.schemas.dto.reply_safety import ClientGuardActivity

MIN_HELD_BACK_REPLIES: int = 5
HELD_BACK_SHARE_NUMERATOR: int = 1
HELD_BACK_SHARE_DENOMINATOR: int = 6
INJECTION_FLAG_SPIKE: int = 10


def is_guard_spike(activity: ClientGuardActivity) -> bool:
    held_back: int = int(activity.rewritten_replies) + int(activity.handed_off_replies)
    checked: int = int(activity.checked_replies)
    is_held_back_often: bool = (
        held_back >= MIN_HELD_BACK_REPLIES
        and held_back * HELD_BACK_SHARE_DENOMINATOR
        >= checked * HELD_BACK_SHARE_NUMERATOR
    )
    return is_held_back_often or int(activity.injection_flags) >= INJECTION_FLAG_SPIKE
