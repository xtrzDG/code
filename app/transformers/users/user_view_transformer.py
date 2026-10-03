from app.contracts.transformer_contract import TransformerContract
from app.schemas.domain.users import UserDocument
from app.schemas.dto.users import UserView


class UserViewTransformer(TransformerContract[UserDocument, UserView]):
    """Shape a stored user for HTTP responses."""

    def transform(self, input_data: UserDocument) -> UserView:
        return UserView(
            id=input_data.id,
            login_method=input_data.login_method,
            phone_number=input_data.phone_number,
            email=input_data.email,
            country_code=input_data.country_code,
            locale=input_data.locale,
            display_name=input_data.display_name,
            is_verified=input_data.is_verified,
            is_platform_admin=input_data.is_platform_admin,
        )
