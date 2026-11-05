from app.contracts.repositories.knowledge_repositories import (
    KnowledgeItemRepoContract,
    ResourceRepoContract,
)
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.deposits import (
    DepositRefusalCode,
    DepositRule,
    PaymentLinkKind,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.deposits import (
    BookingDepositPolicy,
    DepositSettingsDocument,
    TargetedDepositPolicy,
)
from app.schemas.dto.deposits.deposit_settings import (
    DepositPolicyInput,
    DepositPolicyRequest,
    DepositSettingsView,
    SetDepositPolicyCommand,
)
from app.schemas.exceptions.application_errors import NotFoundError
from app.use_cases.deposits.deposit_settings_changes import DepositSettingsChanges
from app.utilities.deposits.deposit_refusals import deposit_refusal


class SetDepositPolicyUseCase(
    UseCaseContract[SetDepositPolicyCommand, DepositSettingsView]
):
    """
    The owner sets the deposit of a resource or a service on its card, or
    of the banquet requests: a fixed sum, a sum per guest or a percent of
    the booking's value, from a number of guests, in the business currency.
    A fixed page fits only a fixed sum (it charges one amount); any rule may
    use a template. A policy set to null is removed. Owners only; audited.
    """

    def __init__(
        self,
        changes: DepositSettingsChanges,
        resource_repo: ResourceRepoContract,
        knowledge_item_repo: KnowledgeItemRepoContract,
    ) -> None:
        self._changes: DepositSettingsChanges = changes
        self._resource_repo: ResourceRepoContract = resource_repo
        self._knowledge_item_repo: KnowledgeItemRepoContract = knowledge_item_repo

    def run(self, input_data: SetDepositPolicyCommand) -> DepositSettingsView:
        business: BusinessDocument = self._changes.owner_business(
            input_data.user_id, input_data.business_id
        )
        request: DepositPolicyRequest = input_data.request
        self._require_target(business, request)

        def edit(settings: DepositSettingsDocument) -> DepositSettingsDocument:
            others: list[TargetedDepositPolicy] = [
                entry for entry in settings.policies if not same_target(entry, request)
            ]
            if request.policy is not None:
                others.append(
                    TargetedDepositPolicy(
                        target=request.target,
                        resource_id=request.resource_id,
                        service_item_id=request.service_item_id,
                        policy=checked_policy(settings, business, request.policy),
                    )
                )
            settings.policies = others
            return settings

        return self._changes.apply(business, input_data.user_id, edit)

    def _require_target(
        self, business: BusinessDocument, request: DepositPolicyRequest
    ) -> None:
        if request.resource_id is not None and (
            self._resource_repo.get(business.id, request.resource_id) is None
        ):
            raise NotFoundError(f"Resource {request.resource_id} was not found.")

        if request.service_item_id is not None and (
            self._knowledge_item_repo.get(business.id, request.service_item_id) is None
        ):
            raise NotFoundError(f"Service {request.service_item_id} was not found.")


def same_target(entry: TargetedDepositPolicy, request: DepositPolicyRequest) -> bool:
    return (
        entry.target is request.target
        and entry.resource_id == request.resource_id
        and entry.service_item_id == request.service_item_id
    )


def checked_policy(
    settings: DepositSettingsDocument,
    business: BusinessDocument,
    policy: DepositPolicyInput,
) -> BookingDepositPolicy:
    if policy.payment_link_id is not None:
        link = next(
            (
                link
                for link in settings.payment_links
                if link.id == policy.payment_link_id
            ),
            None,
        )
        if link is None:
            raise deposit_refusal(
                DepositRefusalCode.NO_PAYMENT_LINK,
                "The payment page is not one of these settings.",
            )

        if link.kind is PaymentLinkKind.STATIC and policy.rule is not DepositRule.FIXED:
            raise deposit_refusal(
                DepositRefusalCode.TEMPLATE_INVALID,
                "A fixed payment page charges one amount: use a template for "
                "deposits per guest or in percent.",
            )

    return BookingDepositPolicy(
        rule=policy.rule,
        amount_minor=policy.amount_minor,
        percent=policy.percent,
        currency_code=business.currency_code,
        min_party_size=policy.min_party_size,
        payment_link_id=policy.payment_link_id,
    )
