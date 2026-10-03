from pathlib import Path

from app.contracts.backups import BackupCipherAdapterContract
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.exceptions.backup_errors import BackupArchiveCorruptError
from app.schemas.typings.backups.constrained_strings import AgeIdentity, AgeRecipient
from app.schemas.typings.platform.strings import LocalFilePath
from app.utilities.security.age.age_header import AgeFormatError
from app.utilities.security.age.age_keys import read_identity, read_recipient
from app.utilities.security.age.age_stream import decrypt_stream, encrypt_stream


class AgeBackupCipherAdapter(BackupCipherAdapterContract):
    """
    Archives in the age v1 format (X25519, ChaCha20-Poly1305), so a backup
    also opens with the `age` command line tool during a manual restore.

    Every recipient of BACKUP_AGE_PUBLIC_KEY can open the archive: the
    restore drill's key and an offline escrow key. Production holds only
    public keys; the identity (BACKUP_AGE_IDENTITY) lives where restores
    happen. A half-written decryption is deleted when the archive turns out
    to be changed or cut off.
    """

    def __init__(
        self,
        recipients: list[AgeRecipient],
        identity: AgeIdentity | None = None,
    ) -> None:
        self._recipients: list[AgeRecipient] = list(recipients)
        self._identity: AgeIdentity | None = identity

    def encrypt_file(self, source: LocalFilePath, target: LocalFilePath) -> None:
        if not self._recipients:
            raise ValidationFailedError(
                "BACKUP_AGE_PUBLIC_KEY is not set: backups are never stored "
                "unencrypted."
            )

        with (
            Path(str(source)).open("rb") as plaintext,
            Path(str(target)).open("wb") as archive,
        ):
            encrypt_stream(
                plaintext,
                archive,
                [read_recipient(recipient) for recipient in self._recipients],
            )

    def decrypt_file(self, source: LocalFilePath, target: LocalFilePath) -> None:
        if self._identity is None:
            raise ValidationFailedError(
                "BACKUP_AGE_IDENTITY is not set: the archive cannot be opened."
            )

        target_path = Path(str(target))
        try:
            with Path(str(source)).open("rb") as archive, target_path.open("wb") as out:
                decrypt_stream(archive, out, read_identity(self._identity))
        except AgeFormatError as error:
            target_path.unlink(missing_ok=True)
            raise BackupArchiveCorruptError(str(error)) from error
