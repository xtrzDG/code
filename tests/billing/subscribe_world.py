"""A business that subscribes from the billing page, with its owner and staff."""

from app.schemas.constants.billing import (
    BillingPeriod,
    InvoiceKind,
    InvoiceStatus,
    PlanKey,
    SetupOption,
)
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.billing_cabinet import (
    CheckoutSessionView,
    StartTrialCommand,
    StartTrialRequest,
    SubscribeCommand,
    SubscribeRequest,
)
from app.schemas.dto.payments import PaymentWebhookReceipt
from app.schemas.typings.billing.constrained_strings import PaymentReturnUrl
from tests.billing.billing_settings import CABINET_ORIGIN, GEORGIA
from tests.billing.billing_testbed import BillingTestbed


class World:
    def __init__(self) -> None:
        self.testbed = BillingTestbed()
        self.owner: UserDocument = self.testbed.add_user(phone_number="+995599123456")
        self.staff: UserDocument = self.testbed.add_user(email="staff@example.com")
        self.business: BusinessDocument = self.testbed.add_business(
            self.owner,
            GEORGIA,
            staff=[self.staff],
        )

    def subscribe(
        self,
        plan_key: PlanKey = PlanKey.VOICE_AND_CHAT,
        billing_period: BillingPeriod = BillingPeriod.MONTHLY,
        return_url: str | None = f"{CABINET_ORIGIN}/billing",
        user: UserDocument | None = None,
        setup_option: SetupOption = SetupOption.DONE_FOR_YOU,
    ) -> CheckoutSessionView:
        """Subscribe and check out; done for you (with the setup fee) by default."""

        return self.testbed.subscribe.execute(
            SubscribeCommand(
                user_id=(user or self.owner).id,
                business_id=self.business.id,
                request=SubscribeRequest(
                    plan_key=plan_key,
                    billing_period=billing_period,
                    setup_option=setup_option,
                    return_url=None
                    if return_url is None
                    else PaymentReturnUrl(return_url),
                ),
            )
        )

    def start_trial(self) -> None:
        self.testbed.start_trial.run(
            StartTrialCommand(
                user_id=self.owner.id,
                business_id=self.business.id,
                request=StartTrialRequest(),
            )
        )
        self.testbed.set_up_for_you(self.business.id)

    def pay(self, session: CheckoutSessionView, payment_id: int = 1) -> None:
        order = self.testbed.payment_order_repo.get(session.payment_order_id)
        assert order is not None
        receipt: PaymentWebhookReceipt = self.testbed.deliver_flitt_callback(
            self.testbed.callback_parameters(order, "approved", payment_id=payment_id)
        )
        assert receipt.payment_order_id == session.payment_order_id

    def open_invoices(self) -> list[InvoiceKind]:
        return [
            invoice.kind
            for invoice in self.testbed.invoices(self.business.id)
            if invoice.status is InvoiceStatus.ISSUED
        ]
