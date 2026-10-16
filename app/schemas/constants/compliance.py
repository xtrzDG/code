from enum import StrEnum


class AuditAction(StrEnum):
    """
    Operation on personal data recorded in the audit log (concept section
    10), a launch decision that must stay traceable (publishing a version
    that has not passed its autotests), or a change of a person's
    two-factor sign-in (an authenticator added or removed, new recovery
    codes): MFA_CHANGED entries name no business. SUPPORT_ACCESS_START and
    SUPPORT_ACCESS_END bound a platform admin's time-boxed look into a
    client's cabinet (with the reason, the address and how it ended);
    SESSION_REVOKED (a person ended sessions of theirs) and
    PLATFORM_ADMIN_CHANGED (the admin team changed) name no business.
    SPEND_LIMIT_REACHED: the business passed its hard daily spend limit and
    its assistant only takes messages for the team until the day ends.
    The ADMIN_* actions are a platform admin's changes to a client's
    account, each with the admin's reason: a longer trial, a discount,
    credit, a waived setup fee, an invoice paid by bank transfer or in
    cash, a plan set by hand.
    """

    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    ADMIN_ACCESS = "admin_access"
    LOGIN = "login"
    RETENTION_PURGE = "retention_purge"
    PUBLISH_UNTESTED = "publish_untested"
    MFA_CHANGED = "mfa_changed"
    SUPPORT_ACCESS_START = "support_access_start"
    SUPPORT_ACCESS_END = "support_access_end"
    SESSION_REVOKED = "session_revoked"
    PLATFORM_ADMIN_CHANGED = "platform_admin_changed"
    SPEND_LIMIT_REACHED = "spend_limit_reached"
    ADMIN_TRIAL_EXTENDED = "admin_trial_extended"
    ADMIN_DISCOUNT_GIVEN = "admin_discount_given"
    ADMIN_CREDIT_GRANTED = "admin_credit_granted"
    ADMIN_SETUP_FEE_WAIVED = "admin_setup_fee_waived"
    ADMIN_INVOICE_MARKED_PAID = "admin_invoice_marked_paid"
    ADMIN_PLAN_OVERRIDDEN = "admin_plan_overridden"


class AuditSecurityEvent(StrEnum):
    """
    The security event an audit entry records beside its action (version 6
    of the entry; the action is one the release before already reads):

    - LOGIN_FAILED (action `login`): a wrong sign-in code or second-factor
      code;
    - OTP_LOCKED and MFA_LOCKED (action `login`): the wrong code that used
      up a sign-in code's or a second step's last attempt;
    - LOGOUT (action `session_revoked`): a person signed out;
    - KEY_ROTATION (action `update` of the encryption keys): a platform
      admin started a key rotation, or the rotation finished.

    Every such entry names no business: it is in the platform's chain and
    the admin audit view.
    """

    LOGIN_FAILED = "login_failed"
    OTP_LOCKED = "otp_locked"
    MFA_LOCKED = "mfa_locked"
    LOGOUT = "logout"
    KEY_ROTATION = "key_rotation"


class AuditChainStatus(StrEnum):
    """
    What the latest check of one audit hash chain found: every entry it
    read links to the one before and hashes to its stored hash (INTACT), or
    something does not (BROKEN).
    """

    INTACT = "intact"
    BROKEN = "broken"


class AuditChainProblem(StrEnum):
    """
    Why a check found an audit hash chain broken, at the first entry that
    fails:

    - HASH_MISMATCH: the entry's content no longer hashes to its hash (it
      was changed after it was written);
    - LINK_BROKEN: the entry does not name the hash of the entry before it
      (an entry before it was changed, removed or put in);
    - POSITION_GAP: a position is missing (an entry was removed);
    - HEAD_LOST: the newest entry a check saw is gone or changed, and no
      purge checkpoint explains it (the end of the chain was cut off or
      rewritten);
    - CHECKPOINT_MISMATCH: entries a purge checkpoint says are gone are
      still there (the checkpoint was moved to hide them).
    """

    HASH_MISMATCH = "hash_mismatch"
    LINK_BROKEN = "link_broken"
    POSITION_GAP = "position_gap"
    HEAD_LOST = "head_lost"
    CHECKPOINT_MISMATCH = "checkpoint_mismatch"
