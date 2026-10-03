"""
Each owner's way from sign-up to paying, read from their account, their
businesses and the product events: the base of the funnel, the tunnel, the
cohorts and the sources.
"""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from typed_time_provider import Microseconds

from app.schemas.constants.analytics import ProductEventName, TunnelStepKey
from app.schemas.constants.niches import NicheKey
from app.schemas.constants.users import BusinessMemberRole
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.product_events import ProductEventDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.analytics.constrained_strings import AcquisitionSourceKey
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.analytics.acquisition_sources import acquisition_source_of

TUNNEL_EVENTS: frozenset[ProductEventName] = frozenset(
    {
        ProductEventName.TUNNEL_STEP_ENTERED,
        ProductEventName.TUNNEL_STEP_COMPLETED,
        ProductEventName.TUNNEL_STEP_SKIPPED,
    }
)


@dataclass(frozen=True)
class BusinessJourney:
    """A business, its owner and when each step first happened to it."""

    business_id: BusinessId
    owner_id: UserId | None
    country_code: CountryCode
    niche_key: NicheKey
    created_at: Microseconds
    first_at: dict[ProductEventName, Microseconds]
    trial_ends_at: Microseconds | None = None


@dataclass(frozen=True)
class OwnerJourney:
    """
    An owner (a person who signed up and created, or may still create, a
    business): when they signed up, where they came from, their businesses
    and when each step first happened to any of them, and the tunnel
    screens they entered, completed and skipped.
    """

    user_id: UserId
    signed_up_at: Microseconds
    country_code: CountryCode | None
    niche_key: NicheKey | None
    source: AcquisitionSourceKey
    businesses: tuple[BusinessJourney, ...]
    first_at: dict[ProductEventName, Microseconds]
    tunnel: dict[ProductEventName, frozenset[TunnelStepKey]] = field(
        default_factory=dict[ProductEventName, frozenset[TunnelStepKey]]
    )

    def reached(self, names: Iterable[ProductEventName]) -> Microseconds | None:
        """When the earliest of these steps happened; None when none did."""

        times: list[Microseconds] = [
            self.first_at[name] for name in names if name in self.first_at
        ]
        return min(times, key=int, default=None)


def build_business_journeys(
    businesses: Sequence[BusinessDocument],
    events: Sequence[ProductEventDocument],
) -> list[BusinessJourney]:
    """Every business with its owner (who created it) and first steps."""

    firsts: dict[BusinessId, dict[ProductEventName, Microseconds]] = defaultdict(dict)
    creators: dict[BusinessId, UserId] = {}
    trial_ends: dict[BusinessId, Microseconds] = {}
    for event in events:
        if event.business_id is None:
            continue

        steps = firsts[event.business_id]
        if event.name not in steps or int(event.occurred_at) < int(steps[event.name]):
            steps[event.name] = event.occurred_at
        if event.name is ProductEventName.BUSINESS_CREATED and event.user_id:
            creators[event.business_id] = event.user_id
        if event.properties.trial_ends_at is not None and (
            event.name is ProductEventName.TRIAL_STARTED
        ):
            trial_ends[event.business_id] = event.properties.trial_ends_at

    return [
        BusinessJourney(
            business_id=business.id,
            owner_id=creators.get(business.id) or first_owner(business),
            country_code=business.country_code,
            niche_key=business.niche_key,
            created_at=business.created_at,
            first_at={
                ProductEventName.BUSINESS_CREATED: business.created_at,
                **firsts.get(business.id, {}),
            },
            trial_ends_at=trial_ends.get(business.id),
        )
        for business in businesses
    ]


def build_owner_journeys(
    users: Sequence[UserDocument],
    business_journeys: Sequence[BusinessJourney],
    member_ids: set[UserId],
    events: Sequence[ProductEventDocument],
) -> list[OwnerJourney]:
    """
    Every owner. Platform admins are left out, and so are invited staff:
    people who joined a business (`member_ids`) without creating one.
    """

    owned: dict[UserId, list[BusinessJourney]] = defaultdict(list)
    for journey in sorted(business_journeys, key=lambda item: int(item.created_at)):
        if journey.owner_id is not None:
            owned[journey.owner_id].append(journey)

    own_events: dict[UserId, list[ProductEventDocument]] = defaultdict(list)
    for event in events:
        if (
            event.user_id is not None
            and event.business_id is None
            or event.user_id is not None
            and event.name in TUNNEL_EVENTS
        ):
            own_events[event.user_id].append(event)

    journeys: list[OwnerJourney] = []
    for user in users:
        businesses: list[BusinessJourney] = owned.get(user.id, [])
        if user.is_platform_admin or (not businesses and user.id in member_ids):
            continue

        journeys.append(owner_journey(user, businesses, own_events.get(user.id, [])))

    return journeys


def owner_journey(
    user: UserDocument,
    businesses: list[BusinessJourney],
    events: list[ProductEventDocument],
) -> OwnerJourney:
    first_at: dict[ProductEventName, Microseconds] = {}
    for step_times in [business.first_at for business in businesses] + [
        {event.name: event.occurred_at} for event in events
    ]:
        for name, occurred_at in step_times.items():
            if name not in first_at or int(occurred_at) < int(first_at[name]):
                first_at[name] = occurred_at

    tunnel: dict[ProductEventName, set[TunnelStepKey]] = defaultdict(set)
    for event in events:
        if event.name in TUNNEL_EVENTS and event.properties.tunnel_step is not None:
            tunnel[event.name].add(event.properties.tunnel_step)

    first: BusinessJourney | None = businesses[0] if businesses else None
    return OwnerJourney(
        user_id=user.id,
        signed_up_at=user.created_at,
        country_code=user.country_code if first is None else first.country_code,
        niche_key=None if first is None else first.niche_key,
        source=acquisition_source_of(user.signup_attribution),
        businesses=tuple(businesses),
        first_at=first_at,
        tunnel={name: frozenset(steps) for name, steps in tunnel.items()},
    )


def first_owner(business: BusinessDocument) -> UserId | None:
    """The first owner among the members (who created a business made
    before product events were recorded)."""

    return next(
        (
            member.user_id
            for member in business.members
            if member.role is BusinessMemberRole.OWNER
        ),
        None,
    )


def invited_member_ids(businesses: Sequence[BusinessDocument]) -> set[UserId]:
    """Everyone on a team who is not its first owner."""

    owners: dict[BusinessId, UserId | None] = {
        business.id: first_owner(business) for business in businesses
    }
    return {
        member.user_id
        for business in businesses
        for member in business.members
        if member.user_id != owners[business.id]
    }
