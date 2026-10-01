import pytest
from base_typed_float import BaseTypedFloatConstraintViolationError
from base_typed_int import BaseTypedIntConstraintViolationError
from base_typed_string import BaseTypedStringConstraintViolationError
from pydantic import BaseModel, ValidationError

from app.schemas.typings.constrained_floats import ExampleConstrainedFloat
from app.schemas.typings.constrained_integers import ExampleConstrainedInt
from app.schemas.typings.constrained_strings import ExampleConstrainedString


class ConstrainedTypingModel(BaseModel):
    count: ExampleConstrainedInt
    name: ExampleConstrainedString
    ratio: ExampleConstrainedFloat


def test_constrained_typings_validate_direct_construction() -> None:
    constrained_count = ExampleConstrainedInt(50)
    constrained_name = ExampleConstrainedString("example")
    constrained_ratio = ExampleConstrainedFloat(0.75)

    assert type(constrained_count) is ExampleConstrainedInt
    assert type(constrained_name) is ExampleConstrainedString
    assert type(constrained_ratio) is ExampleConstrainedFloat

    with pytest.raises(BaseTypedFloatConstraintViolationError):
        ExampleConstrainedFloat(1.5)

    with pytest.raises(BaseTypedIntConstraintViolationError):
        ExampleConstrainedInt(51)

    with pytest.raises(BaseTypedStringConstraintViolationError):
        ExampleConstrainedString("EXAMPLE")


def test_constrained_typings_preserve_types_in_pydantic_models() -> None:
    model = ConstrainedTypingModel.model_validate(
        {
            "count": 50,
            "name": "example",
            "ratio": 0.75,
        }
    )

    assert type(model.count) is ExampleConstrainedInt
    assert type(model.name) is ExampleConstrainedString
    assert type(model.ratio) is ExampleConstrainedFloat

    with pytest.raises(ValidationError):
        ConstrainedTypingModel.model_validate(
            {
                "count": 51,
                "name": "EXAMPLE",
                "ratio": 1.5,
            }
        )


def test_constrained_typings_expose_constraints_in_json_schema() -> None:
    properties_schema = ConstrainedTypingModel.model_json_schema()["properties"]

    assert properties_schema["count"] == {
        "maximum": 100,
        "minimum": 0,
        "multipleOf": 5,
        "title": "Count",
        "type": "integer",
    }
    assert properties_schema["name"] == {
        "maxLength": 20,
        "minLength": 3,
        "pattern": "^[a-z]+$",
        "title": "Name",
        "type": "string",
    }
    assert properties_schema["ratio"] == {
        "maximum": 1.0,
        "minimum": 0.0,
        "title": "Ratio",
        "type": "number",
    }
