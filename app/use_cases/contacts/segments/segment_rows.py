"""A segment's member as one CSV row, in the order of SEGMENT_CSV_COLUMNS."""

from zoneinfo import ZoneInfo

from app.schemas.dto.contacts import ContactSummaryView
from app.schemas.dto.privacy.csv_exports import CsvRow
from app.utilities.privacy.csv_cells import flag_cell, list_cell, moment_cell, text_cell


def member_row(member: ContactSummaryView, zone: ZoneInfo) -> CsvRow:
    return CsvRow(
        cells=[
            text_cell(member.id),
            text_cell(member.name),
            text_cell(member.phone_number),
            flag_cell(member.is_phone_verified),
            text_cell(member.language),
            list_cell(member.channels),
            list_cell(member.tags),
            flag_cell(member.is_vip),
            text_cell(member.booking_count),
            moment_cell(member.last_activity_at, zone),
            list_cell(member.opted_out_channels),
        ]
    )
