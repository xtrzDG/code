"""An owner, staff, an admin and their business behind the billing HTTP routes."""

from fastapi.testclient import TestClient

from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.payments import PaymentOrderDocument
from app.schemas.domain.users import UserDocument
from app.schemas.typings.billing.prefixed_id import PaymentOrderId
from tests.billing.billing_settings import CABINET_ORIGIN, GEORGIA
from tests.billing.billing_testbed import BillingTestbed, bearer


class RouteWorld:
    def __init__(self) -> None:
        self.testbed = BillingTestbed()
        self.client: TestClient = self.testbed.build_http_client()
        self.owner: UserDocument = self.testbed.add_user(phone_number="+995599123456")
        self.staff: UserDocument = self.testbed.add_user(email="staff@example.com")
        self.admin: UserDocument = self.testbed.add_user(
            email="dani@example.com",
            is_platform_admin=True,
        )
        self.business: BusinessDocument = self.testbed.add_business(
            self.owner,
            GEORGIA,
            staff=[self.staff],
        )

    def billing_path(self, suffix: str = "") -> str:
        return f"/v1/businesses/{self.business.id}/billing{suffix}"

    def start_trial(self) -> None:
        response = self.client.post(
            self.billing_path("/trial"),
            headers=bearer(self.owner),
        )
        assert response.status_code == 201

    def checkout(self) -> PaymentOrderDocument:
        response = self.client.post(
            self.billing_path("/checkout"),
            headers=bearer(self.owner),
            json={"return_url": f"{CABINET_ORIGIN}/billing"},
        )
        assert response.status_code == 201
        order = self.testbed.payment_order_repo.get(
            PaymentOrderId(response.json()["payment_order_id"])
        )
        assert order is not None
        return order
