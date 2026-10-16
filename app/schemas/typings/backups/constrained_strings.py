"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class AgeIdentity(BaseConstrainedTypedString):
    """
    The private key that opens database backups (an age X25519 identity,
    `AGE-SECRET-KEY-1...`, Bech32). Only the restore drill and the people
    who restore hold it; production never does. Never logged.

    Example:
        identity = AgeIdentity(os.environ["BACKUP_AGE_IDENTITY"])
    """

    min_length = 74
    max_length = 74
    pattern = r"^AGE-SECRET-KEY-1[02-9AC-HJ-NP-Z]{58}\Z"


class AgeRecipient(BaseConstrainedTypedString):
    """
    A public key database backups are encrypted to (an age X25519
    recipient, `age1...`, Bech32). Anyone may hold it: it only locks.

    Example:
        recipient = AgeRecipient(public_key_text)  # "age1ql3z7hjy54pw..."
    """

    min_length = 62
    max_length = 62
    pattern = r"^age1[02-9ac-hj-np-z]{58}\Z"


class BackupChecksum(BaseConstrainedTypedString):
    """
    SHA-256 (lowercase hex) of an encrypted backup archive as uploaded: the
    restore drill checks the downloaded bytes against it.

    Example:
        checksum = BackupChecksum(hashlib.sha256(archive).hexdigest())
    """

    min_length = 64
    max_length = 64
    pattern = r"^[0-9a-f]{64}\Z"


class BackupObjectKey(BaseConstrainedTypedString):
    """
    The key of one object in the backup bucket (an archive, its manifest,
    or anything else listed under the prefix). Printable, without spaces
    or control characters.

    Example:
        key = BackupObjectKey("workshop/2026/10/workshop-20261003T010700Z.age")
    """

    min_length = 1
    max_length = 1024
    pattern = r"^[\x21-\x7e]+\Z"


class BackupObjectPrefix(BaseConstrainedTypedString):
    """
    The "folder" of the backup bucket the archives live under
    (BACKUP_S3_PREFIX): one to four lowercase segments, each ending in "/".
    Retention never touches anything outside it.

    Example:
        prefix = BackupObjectPrefix("workshop/")
    """

    min_length = 2
    max_length = 256
    pattern = r"^([a-z0-9][a-z0-9._-]{0,62}/){1,4}\Z"


class DatabaseTableName(BaseConstrainedTypedString):
    """
    A table of the database, qualified with its schema: what the backup
    manifest counts rows of and the restore drill compares.

    Example:
        table = DatabaseTableName("workshop.bookings")
    """

    min_length = 3
    max_length = 127
    pattern = r"^[a-z_][a-z0-9_]{0,62}\.[a-z_][a-z0-9_]{0,62}\Z"


class ScratchDatabaseName(BaseConstrainedTypedString):
    """
    The throwaway database a restore drill restores into and drops again
    (`restore_drill_<time>_<random>`), never one the platform uses.

    Example:
        name = ScratchDatabaseName("restore_drill_20261003t010700_3f9a1c")
    """

    min_length = 14
    max_length = 63
    pattern = r"^restore_drill_[a-z0-9_]{1,49}\Z"


# Keep abc order for all non example types, if possible.
