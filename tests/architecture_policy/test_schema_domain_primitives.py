import ast
from dataclasses import dataclass
from pathlib import Path

SCHEMA_DIRECTORY_PATHS: tuple[str, ...] = (
    "app/schemas/dto",
    "app/schemas/domain",
)
RAW_PRIMITIVE_NAMES: frozenset[str] = frozenset(
    {"str", "int", "float", "UUID"},
)
ALLOWED_RAW_PRIMITIVE_FIELD_PATHS: list[str] = []


@dataclass(frozen=True)
class RawPrimitiveField:
    field_path: str
    raw_primitive_name: str


def test_schema_domain_fields_use_project_primitives() -> None:
    project_root_path: Path = Path(__file__).resolve().parents[2]
    allowed_field_paths: set[str] = set(ALLOWED_RAW_PRIMITIVE_FIELD_PATHS)
    raw_primitive_fields: list[RawPrimitiveField] = []

    for schema_directory_path in SCHEMA_DIRECTORY_PATHS:
        absolute_schema_directory_path: Path = project_root_path / schema_directory_path
        for schema_module_path in sorted(absolute_schema_directory_path.glob("*.py")):
            if schema_module_path.name == "__init__.py":
                continue

            raw_primitive_fields.extend(
                collect_raw_primitive_fields(
                    schema_module_path=schema_module_path,
                    project_root_path=project_root_path,
                    allowed_field_paths=allowed_field_paths,
                ),
            )

    assert raw_primitive_fields == [], (
        "Raw schema primitives are forbidden for domain-owned fields. "
        "Use app/schemas/typings primitives instead.\n\n"
        "Do not add exceptions by default. Architecture principles forbid "
        "expanding ALLOWED_RAW_PRIMITIVE_FIELD_PATHS unless the author "
        "explicitly confirms that this field cannot use a typed primitive.\n\n"
        "Unexpected raw primitive fields: "
        f"{format_raw_primitive_fields(raw_primitive_fields)}"
    )


def collect_raw_primitive_fields(
    schema_module_path: Path,
    project_root_path: Path,
    allowed_field_paths: set[str],
) -> list[RawPrimitiveField]:
    module_source: str = schema_module_path.read_text(encoding="utf-8")
    module_ast: ast.Module = ast.parse(module_source, filename=str(schema_module_path))
    relative_module_path: str = schema_module_path.relative_to(
        project_root_path
    ).as_posix()
    raw_primitive_fields: list[RawPrimitiveField] = []

    for module_statement in module_ast.body:
        if not isinstance(module_statement, ast.ClassDef):
            continue

        for class_statement in module_statement.body:
            if not isinstance(class_statement, ast.AnnAssign):
                continue

            if not isinstance(class_statement.target, ast.Name):
                continue

            field_path: str = (
                f"{relative_module_path}::{module_statement.name}."
                f"{class_statement.target.id}"
            )
            if field_path in allowed_field_paths:
                continue

            raw_primitive_names: list[str] = collect_raw_primitive_names(
                class_statement.annotation,
            )
            for raw_primitive_name in raw_primitive_names:
                raw_primitive_fields.append(
                    RawPrimitiveField(
                        field_path=field_path,
                        raw_primitive_name=raw_primitive_name,
                    ),
                )

    return raw_primitive_fields


def collect_raw_primitive_names(annotation: ast.expr) -> list[str]:
    annotation_nodes: list[ast.expr] = collect_top_level_annotation_nodes(annotation)
    raw_primitive_names: list[str] = []

    for annotation_node in annotation_nodes:
        raw_primitive_name: str | None = raw_primitive_name_from_annotation_node(
            annotation_node,
        )
        if raw_primitive_name is None:
            continue

        if raw_primitive_name in raw_primitive_names:
            continue

        raw_primitive_names.append(raw_primitive_name)

    return raw_primitive_names


def collect_top_level_annotation_nodes(annotation: ast.expr) -> list[ast.expr]:
    annotation_nodes: list[ast.expr] = [annotation]
    annotation_nodes.extend(collect_direct_child_annotation_nodes(annotation))

    for annotation_node in list(annotation_nodes):
        annotation_nodes.extend(collect_direct_child_annotation_nodes(annotation_node))

    return annotation_nodes


def collect_direct_child_annotation_nodes(annotation_node: ast.expr) -> list[ast.expr]:
    child_annotation_nodes: list[ast.expr] = []

    if isinstance(annotation_node, ast.Subscript):
        child_annotation_nodes.extend(
            collect_subscript_slice_annotation_nodes(annotation_node),
        )

    if isinstance(annotation_node, ast.BinOp) and isinstance(
        annotation_node.op,
        ast.BitOr,
    ):
        child_annotation_nodes.append(annotation_node.left)
        child_annotation_nodes.append(annotation_node.right)

    return child_annotation_nodes


def collect_subscript_slice_annotation_nodes(
    annotation_node: ast.Subscript,
) -> list[ast.expr]:
    subscript_slice_node: ast.expr = annotation_node.slice

    if isinstance(subscript_slice_node, ast.Tuple):
        return list(subscript_slice_node.elts)

    return [subscript_slice_node]


def raw_primitive_name_from_annotation_node(annotation_node: ast.expr) -> str | None:
    if (
        isinstance(annotation_node, ast.Name)
        and annotation_node.id in RAW_PRIMITIVE_NAMES
    ):
        return annotation_node.id

    if is_uuid_attribute(annotation_node):
        return "uuid.UUID"

    return None


def is_uuid_attribute(annotation_node: ast.AST) -> bool:
    if not isinstance(annotation_node, ast.Attribute):
        return False

    if annotation_node.attr != "UUID":
        return False

    return (
        isinstance(annotation_node.value, ast.Name)
        and annotation_node.value.id == "uuid"
    )


def format_raw_primitive_fields(raw_primitive_fields: list[RawPrimitiveField]) -> str:
    formatted_fields: list[str] = []
    for raw_primitive_field in raw_primitive_fields:
        formatted_field: str = (
            f"{raw_primitive_field.field_path} "
            f"({raw_primitive_field.raw_primitive_name})"
        )
        formatted_fields.append(
            formatted_field,
        )

    return ", ".join(formatted_fields)
