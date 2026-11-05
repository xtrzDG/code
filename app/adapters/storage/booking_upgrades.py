"""
Upcasters of the stored bookings (`document_upgrades` registers them).

Version 5 names the booking as the platform wrote it to the booking system
its resource follows (`booking_system_booking`). Writing bookings there
began with version 5, so an older booking was written nowhere: it gets the
field empty, and a later change of the booking writes it as it is then.
"""

# Stored JSON of one document, before validation (the storage boundary).
type StoredJsonObject = dict[str, object]


def upgrade_bookings_from_v4(document: StoredJsonObject) -> StoredJsonObject:
    upgraded: StoredJsonObject = dict(document)
    upgraded.setdefault("booking_system_booking", None)
    return upgraded
