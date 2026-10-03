"""
Archives open with the `age` command line tool and the other way round,
so a manual restore needs nothing of this code base. Skipped where `age`
is not installed (CI installs it).
"""

import os
import shutil
import subprocess  # nosec B404 - runs the age tool in a test
from pathlib import Path

import pytest

from app.adapters.backup.age_backup_cipher_adapter import AgeBackupCipherAdapter
from app.schemas.typings.backups.constrained_strings import AgeIdentity, AgeRecipient
from app.schemas.typings.platform.strings import LocalFilePath
from app.utilities.security.age.age_keys import generate_identity, recipient_of

AGE: str | None = shutil.which("age")
pytestmark = pytest.mark.skipif(AGE is None, reason="the age tool is not installed")


def write_identity_file(directory: Path, identity: AgeIdentity) -> Path:
    path = directory / "key.txt"
    path.write_text(f"{identity}\n", encoding="ascii")
    return path


@pytest.mark.parametrize("size", [0, 65536, 300_000])
def test_age_opens_our_archives(tmp_path: Path, size: int) -> None:
    identity = generate_identity()
    plaintext = os.urandom(size)
    (tmp_path / "dump").write_bytes(plaintext)
    AgeBackupCipherAdapter([recipient_of(identity)]).encrypt_file(
        LocalFilePath(str(tmp_path / "dump")), LocalFilePath(str(tmp_path / "dump.age"))
    )

    opened = subprocess.run(  # nosec B603 - fixed test command
        [
            str(AGE),
            "--decrypt",
            "--identity",
            str(write_identity_file(tmp_path, identity)),
            str(tmp_path / "dump.age"),
        ],
        capture_output=True,
        check=True,
    )

    assert opened.stdout == plaintext


def test_we_open_archives_of_age(tmp_path: Path) -> None:
    identity = generate_identity()
    recipient: AgeRecipient = recipient_of(identity)
    plaintext = os.urandom(150_000)
    (tmp_path / "dump").write_bytes(plaintext)
    subprocess.run(  # nosec B603 - fixed test command
        [
            str(AGE),
            "--recipient",
            str(recipient),
            "--output",
            str(tmp_path / "dump.age"),
            str(tmp_path / "dump"),
        ],
        check=True,
    )

    AgeBackupCipherAdapter([recipient], identity).decrypt_file(
        LocalFilePath(str(tmp_path / "dump.age")),
        LocalFilePath(str(tmp_path / "opened")),
    )

    assert (tmp_path / "opened").read_bytes() == plaintext
