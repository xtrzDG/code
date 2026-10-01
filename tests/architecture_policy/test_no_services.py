from pathlib import Path


def test_services_directory_contains_only_readme() -> None:
    project_root_path: Path = Path(__file__).resolve().parents[2]
    services_directory_path: Path = project_root_path / "app" / "services"
    services_readme_file_path: Path = services_directory_path / "README.md"

    assert services_directory_path.is_dir()
    assert services_readme_file_path.is_file()
    assert not (services_directory_path / "__init__.py").exists()

    unexpected_service_file_paths: list[Path] = []
    for service_file_path in services_directory_path.rglob("*"):
        if not service_file_path.is_file():
            continue

        if service_file_path != services_readme_file_path:
            unexpected_service_file_paths.append(service_file_path)

    assert unexpected_service_file_paths == [], (
        "`app/services/` may contain only README.md. Do not add Python files here "
        "and do not turn it into a package. Move behavior to the concrete "
        "architectural role it actually owns: use_cases, orchestrators, pipelines, "
        "operators, repositories, registries, facilitators, utilities, adapters, "
        "clients, gateways, or transformers. Unexpected files: "
        f"{format_paths(unexpected_service_file_paths, project_root_path)}"
    )


def format_paths(file_paths: list[Path], project_root_path: Path) -> str:
    relative_paths: list[str] = []
    for file_path in file_paths:
        relative_paths.append(file_path.relative_to(project_root_path).as_posix())

    return ", ".join(relative_paths)
