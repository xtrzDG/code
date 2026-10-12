"""
A website visitor's photo or voice note (POST /v1/widget/{id}/attachments):
its type is read from its bytes, its size and length are checked by the
API, photos lose their metadata, uploads are counted before they are read,
and a file belongs to the visitor who uploaded it.
"""

from typing import Any

from app.schemas.constants.businesses import BusinessStatus
from app.schemas.constants.channels import ChannelStatus
from app.utilities.channels.widget_visitors import widget_visitor_id
from app.utilities.media.media_paths import WIDGET_UPLOAD_DIRECTORY
from tests.channels.test_widget import SESSION_KEY
from tests.channels.widget_upload_bed import OTHER_VISITOR, WidgetUploadBed
from tests.media.media_fakes import ogg_opus_bytes
from tests.media.upload_files import (
    COMMENT_TEXT,
    DEVICE_TEXT,
    GPS_TEXT,
    jpeg_photo,
    mp4_recording,
    png_photo,
    webm_recording,
    webp_photo,
)


def error_code(response: Any) -> str:
    body: dict[str, Any] = response.json()
    reasons: list[dict[str, str]] = body.get("reasons") or []
    return reasons[0]["code"] if reasons else str(body["error"])


class TestTypes:
    def test_a_photo_is_kept_for_its_visitor_without_its_metadata(self) -> None:
        bed = WidgetUploadBed()

        response = bed.upload(jpeg_photo(orientation=6), "image/jpeg")

        assert response.status_code == 201
        assert response.headers["Access-Control-Allow-Origin"] == "*"
        view = response.json()
        assert view["attachment_id"].startswith("widget_upload_")
        assert (view["kind"], view["media_type"]) == ("image", "image/jpeg")
        assert view["duration_seconds"] is None
        upload = bed.stored_upload(view["attachment_id"])
        assert upload.visitor_id == widget_visitor_id(SESSION_KEY)
        assert str(upload.storage_path).startswith(
            f"{WIDGET_UPLOAD_DIRECTORY}/{bed.business.id}/"
        )
        stored = bed.stored_bytes(view["attachment_id"])
        assert stored.startswith(b"\xff\xd8") and stored.endswith(b"\xff\xd9")
        for personal in (GPS_TEXT, DEVICE_TEXT, COMMENT_TEXT):
            assert personal not in stored
        # The rotation survives in an Exif block of its own.
        assert b"Exif\x00\x00MM" in stored
        assert view["byte_count"] == len(stored)

    def test_png_and_webp_photos_lose_their_text_and_exif(self) -> None:
        bed = WidgetUploadBed()

        png_id = bed.uploaded_id(png_photo(), "image/png")
        webp_id = bed.uploaded_id(webp_photo(), "image/webp")

        png = bed.stored_bytes(png_id)
        webp = bed.stored_bytes(webp_id)
        assert b"tEXt" not in png and b"eXIf" not in png and b"IDAT" in png
        assert b"EXIF" not in webp and b"XMP " not in webp and b"VP8L" in webp
        assert COMMENT_TEXT not in png and GPS_TEXT not in webp

    def test_voice_notes_of_every_browser_are_measured(self) -> None:
        bed = WidgetUploadBed()

        recordings = [
            (webm_recording(8), "audio/webm;codecs=opus"),
            (ogg_opus_bytes(seconds=5), "audio/ogg"),
            (mp4_recording(12), "audio/mp4"),
        ]
        views = [bed.upload(*recording).json() for recording in recordings]

        assert [view["duration_seconds"] for view in views] == [8, 5, 12]
        assert [view["media_type"] for view in views] == [
            "audio/webm",
            "audio/ogg",
            "audio/mp4",
        ]
        assert {view["kind"] for view in views} == {"audio"}

    def test_a_type_the_chat_does_not_take_is_refused(self) -> None:
        bed = WidgetUploadBed()

        for content, declared in [
            (b"GIF89a" + bytes(32), "image/gif"),
            (b"%PDF-1.7" + bytes(32), "application/pdf"),
            (b"<svg xmlns='http://www.w3.org/2000/svg'/>", "image/svg+xml"),
        ]:
            response = bed.upload(content, declared)
            assert response.status_code == 422
            assert error_code(response) == "unsupported_type"

        assert bed.testbed.media_storage.files == {}

    def test_bytes_that_are_not_the_declared_type_are_refused(self) -> None:
        bed = WidgetUploadBed()

        cases = [
            (jpeg_photo(), "image/png"),
            (b"<html><script>alert(1)</script></html>" + bytes(16), "image/jpeg"),
            (png_photo(), "audio/webm"),
            (webm_recording(3), "audio/ogg"),
        ]
        codes = [error_code(bed.upload(*case)) for case in cases]

        assert codes == ["type_mismatch"] * len(cases)
        assert bed.testbed.media_storage.files == {}

    def test_a_recording_with_video_is_not_a_voice_note(self) -> None:
        bed = WidgetUploadBed()

        webm_video = bed.upload(webm_recording(4, track_types=(2, 1)), "audio/webm")
        mp4_video = bed.upload(mp4_recording(4, (b"soun", b"vide")), "audio/mp4")
        broken = bed.upload(b"\xff\xd8\xff\xe0" + bytes(40), "image/jpeg")

        assert error_code(webm_video) == "unreadable_file"
        assert error_code(mp4_video) == "unreadable_file"
        assert error_code(broken) == "unreadable_file"
        assert bed.testbed.media_storage.files == {}


class TestSizeAndLength:
    def test_a_photo_over_its_cap_is_refused(self) -> None:
        bed = WidgetUploadBed()
        photo = jpeg_photo(trailer=bytes(70_000))

        response = bed.upload(photo, "image/jpeg")

        assert response.status_code == 422
        assert error_code(response) == "file_too_large"
        assert response.json()["reasons"][0]["details"] == ["65536"]
        assert bed.testbed.media_storage.files == {}

    def test_a_body_over_the_largest_cap_is_not_read_to_its_end(self) -> None:
        bed = WidgetUploadBed()
        oversized = bytes(131_072 + 32 * 1024)

        response = bed.upload(b"\xff\xd8\xff" + oversized, "image/jpeg")

        assert response.status_code == 422
        assert error_code(response) == "file_too_large"

    def test_a_voice_note_longer_than_allowed_is_refused(self) -> None:
        bed = WidgetUploadBed()

        too_long = bed.upload(webm_recording(61), "audio/webm")
        just_fits = bed.upload(webm_recording(60), "audio/webm")

        assert error_code(too_long) == "voice_too_long"
        assert just_fits.status_code == 201

    def test_a_form_without_exactly_one_file_part_is_refused(self) -> None:
        bed = WidgetUploadBed()
        path = f"/v1/widget/{bed.business.id}/attachments"
        headers = {"X-Widget-Session-Key": SESSION_KEY}

        no_file = bed.client.post(path, headers=headers, data={"note": "hi"})
        two_files = bed.client.post(
            path,
            headers=headers,
            files=[
                ("file", ("a.png", png_photo(), "image/png")),
                ("file", ("b.png", png_photo(), "image/png")),
            ],
        )
        not_a_form = bed.client.post(path, headers=headers, content=png_photo())

        assert [no_file.status_code, two_files.status_code] == [422, 422]
        assert not_a_form.status_code == 422
        assert bed.testbed.media_storage.files == {}


class TestAdmission:
    def test_uploads_are_counted_before_the_file_is_read(self) -> None:
        bed = WidgetUploadBed()

        answers = [bed.upload(png_photo(), "image/png").status_code for _ in range(6)]
        limited = bed.upload(png_photo(), "image/png")
        other_visitor = bed.upload(png_photo(), "image/png", session_key=OTHER_VISITOR)

        assert answers == [201] * 6
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) > 0
        assert other_visitor.status_code == 201
        assert len(bed.testbed.media_storage.files) == 7

    def test_a_chat_that_is_off_or_not_live_takes_no_files(self) -> None:
        bed = WidgetUploadBed()
        [channel] = bed.testbed.channel_repo.list_by_business(bed.business.id)

        bed.business.status = BusinessStatus.PAUSED
        bed.testbed.business_repo.save(bed.business)
        paused = bed.upload(png_photo(), "image/png")
        channel.status = ChannelStatus.DISABLED
        bed.testbed.channel_repo.save(channel)
        switched_off = bed.upload(png_photo(), "image/png")
        unknown = bed.upload(png_photo(), "image/png", business_id="business_x")

        assert paused.status_code == 409
        assert switched_off.status_code == 404
        assert unknown.status_code == 404
        assert bed.testbed.media_storage.files == {}

    def test_a_visitor_without_a_session_key_is_refused(self) -> None:
        bed = WidgetUploadBed()

        response = bed.client.post(
            f"/v1/widget/{bed.business.id}/attachments",
            files={"file": ("a.png", png_photo(), "image/png")},
        )
        bad_key = bed.upload(png_photo(), "image/png", session_key="x")

        assert response.status_code == 422
        assert bad_key.status_code == 422

    def test_the_preflight_allows_the_session_key_header(self) -> None:
        bed = WidgetUploadBed()

        response = bed.client.options(f"/v1/widget/{bed.business.id}/attachments")

        assert response.status_code == 204
        assert (
            "X-Widget-Session-Key" in response.headers["Access-Control-Allow-Headers"]
        )
