"""Masters and services named in any script find their stored names."""

import pytest

from app.schemas.constants.bookings import BookingRefusalCode
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.bookings.strings import ResourceName
from app.utilities.bookings.name_matching import best_name_matches, name_match_score
from app.utilities.bookings.name_spellings import (
    consonant_skeleton,
    is_abjad_text,
    spell_name_in_latin,
)
from tests.bookings.salon_fixture import Salon, reason_code


@pytest.mark.parametrize("written", ["ნინო", "Нино", "Νίνο", "NINO", "nino"])
def test_a_georgian_cyrillic_or_greek_name_books_the_latin_master(
    written: str,
) -> None:
    salon = Salon()

    result = salon.book(service="Haircut", resource=written, time="14:00")

    assert result.booking.resource_name == "Nino"
    assert result.booking.resource_id == salon.nino.id


@pytest.mark.parametrize(
    ("written", "master"),
    [("לוין", "Levan"), ("نينو", "Nino"), ("מרים", "Mariam"), ("مريم", "Mariam")],
)
def test_a_name_without_vowels_matches_by_its_consonants(
    written: str, master: str
) -> None:
    salon = Salon()
    service = "Manicure" if master == "Mariam" else "Haircut"

    result = salon.book(service=service, resource=written, time="14:00")

    assert result.booking.resource_name == master


def test_an_inflected_georgian_name_finds_the_master() -> None:
    salon = Salon()

    # "მარიამი" (nominative with its ending) is the Latin "Mariam".
    result = salon.query(service="Manicure", resource="მარიამი", time="12:00")

    assert {slot.resource_name for slot in result.slots} == {"Mariam"}


def test_a_service_written_in_its_own_script_and_inflected_is_found() -> None:
    salon = Salon()
    salon.offer("Стрижка бороды", 30, 2500, performers=[salon.levan])

    # "стрижку бороды": the accusative a Russian speaker writes.
    result = salon.book(service="стрижку бороды", time="16:00")

    assert result.booking.resource_name == "Levan"
    assert result.booking.service_title == "Стрижка бороды"
    assert result.booking.end_time == "16:30"


def test_an_unknown_name_lists_who_can_be_booked() -> None:
    salon = Salon()

    with pytest.raises(ValidationFailedError, match="Nobody and nothing") as error:
        salon.book(service="Haircut", resource="გიორგი")

    assert reason_code(error.value) == BookingRefusalCode.UNKNOWN_RESOURCE
    assert error.value.reasons[0].details == []
    for master in (salon.nino, salon.levan, salon.mariam):
        assert f"{master.name} (id {master.id})" in str(error.value)


def test_two_masters_with_the_same_first_name_are_ambiguous() -> None:
    salon = Salon()
    second = salon.staff("Nino Kapanadze")
    renamed = salon.nino.model_copy(update={"name": ResourceName("Nino Beridze")})
    salon.world.resource_repo.save(renamed)

    with pytest.raises(ValidationFailedError, match="matches several") as error:
        salon.book(service="Haircut", resource="ნინო")

    assert reason_code(error.value) == BookingRefusalCode.AMBIGUOUS_RESOURCE
    assert set(error.value.reasons[0].details) == {str(salon.nino.id), str(second.id)}
    # The full name settles it.
    result = salon.book(service="Haircut", resource="Нино Беридзе", time="15:00")
    assert result.booking.resource_id == salon.nino.id


def test_a_resource_is_found_by_its_id() -> None:
    salon = Salon()

    result = salon.book(service="Haircut", resource=str(salon.levan.id), time="17:00")

    assert result.booking.resource_name == "Levan"


def test_name_scores_prefer_the_exact_name_and_the_whole_name() -> None:
    assert name_match_score("ნინო", "Nino") == 1.0
    assert name_match_score("Nino", "Nino Beridze") < name_match_score("Nino", "Nino")
    assert name_match_score("Nino", "Nino Beridze") >= 0.5
    assert name_match_score("Levan", "Nino") == 0.0
    assert name_match_score("", "Nino") == 0.0
    assert name_match_score("...", "Nino") == 0.0


def test_best_matches_keep_only_the_equally_good_ones() -> None:
    names = [("a", "Hair colouring"), ("b", "Hair styling"), ("c", "Manicure")]

    assert [match.item for match in best_name_matches("hair", names)] == ["a", "b"]
    assert [match.item for match in best_name_matches("colouring", names)] == ["a"]
    assert best_name_matches("pedicure", names) == []


def test_latin_spellings_and_consonant_skeletons() -> None:
    assert spell_name_in_latin("ნინო") == "nino"
    assert spell_name_in_latin("Νίνο") == "nino"
    assert spell_name_in_latin("Нино") == "nino"
    assert is_abjad_text("לוין") and is_abjad_text("ليفان")
    assert not is_abjad_text("Levan")
    assert consonant_skeleton(spell_name_in_latin("לוין")) == consonant_skeleton(
        "levan"
    )
