"""
Privacy by default (GDPR art. 25): a business created from 3 November 2026
on starts with the nightly quality sample off until its owner turns it on;
a business created before keeps what it had (on, unless its owner turned
it off), and a stored choice always wins.
"""

from typed_time_provider import Microseconds

from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.dto.retention import (
    PrivacySettingsQuery,
    PrivacySettingsRequest,
    UpdatePrivacySettingsCommand,
)
from app.schemas.typings.privacy.constrained_integers import (
    ConversationRetentionDays,
    LlmTurnRetentionDays,
)
from app.utilities.privacy.quality_sampling_defaults import (
    QUALITY_SAMPLING_OFF_FOR_BUSINESSES_FROM,
    default_privacy_settings,
    default_quality_sampling,
)
from tests.privacy.test_privacy_settings import PrivacyBed
from tests.quality.quality_bench import CountingJudge, QualityBench, tick, verdict

CUT_OFF: int = int(QUALITY_SAMPLING_OFF_FOR_BUSINESSES_FROM)


def created(business: BusinessDocument, at: int) -> BusinessDocument:
    return business.model_copy(update={"created_at": Microseconds(at)})


def test_a_business_created_from_the_cut_off_starts_with_the_sample_off() -> None:
    bed = PrivacyBed()
    older = created(bed.business, CUT_OFF - 1)
    newer = created(bed.business, CUT_OFF)

    assert default_quality_sampling(older) is True
    assert default_quality_sampling(newer) is False
    assert bed.settings.get_or_default(older).quality_sampling_allowed is True
    assert bed.settings.get_or_default(newer).quality_sampling_allowed is False
    assert default_privacy_settings(newer).business_id == newer.id


def test_the_owner_of_a_new_business_sees_it_off_and_saving_keeps_it_off() -> None:
    bed = PrivacyBed()
    bed.business = created(bed.business, CUT_OFF + 1)
    bed.testbed.business_repo.save(bed.business)

    view = bed.get.run(
        PrivacySettingsQuery(user_id=bed.owner_id, business_id=bed.business.id)
    )
    bed.change(conversations=730, model_records=30)

    assert view.quality_sampling_allowed is False
    assert bed.settings.get_or_default(bed.business).quality_sampling_allowed is False


def test_a_stored_choice_wins_over_the_default_either_way() -> None:
    bed = PrivacyBed()
    bed.business = created(bed.business, CUT_OFF + 1)
    bed.testbed.business_repo.save(bed.business)

    bed.update.run(
        UpdatePrivacySettingsCommand(
            user_id=bed.owner_id,
            business_id=bed.business.id,
            request=PrivacySettingsRequest(
                conversation_retention_days=ConversationRetentionDays(730),
                llm_turn_retention_days=LlmTurnRetentionDays(30),
                quality_sampling_allowed=True,
            ),
        )
    )
    older = created(bed.business, CUT_OFF - 1)
    stored_off = BusinessPrivacySettingsDocument(
        id=bed.settings.get_or_default(older).id,
        business_id=older.id,
        quality_sampling_allowed=False,
    )

    assert bed.settings.get_or_default(bed.business).quality_sampling_allowed is True
    bed.settings.save(stored_off)
    assert bed.settings.get_or_default(older).quality_sampling_allowed is False


def test_the_nightly_sample_reads_an_older_business_but_never_a_new_one() -> None:
    bench = QualityBench()
    older = bench.live_business()
    newer = bench.live_business()
    newer.created_at = Microseconds(CUT_OFF + 1)
    bench.world.business_repo.save(newer)
    kept = bench.conversation(older)
    bench.conversation(newer)

    report = bench.job(CountingJudge(lambda _request: verdict())).run(tick(bench))

    assert int(report.processed_count) == 1
    assert [score.conversation_id for score in bench.stored_scores()] == [kept.id]
