import ast
from pathlib import Path


FORBIDDEN_IMPORT_PREFIXES = ("sqlalchemy", "psycopg", "app.infrastructure")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_phase4_domain_models_and_storage_contract_do_not_depend_on_infrastructure() -> None:
    app_root = Path(__file__).resolve().parents[2]
    paths = (
        app_root / "domain" / "models" / "session.py",
        app_root / "domain" / "models" / "frame.py",
        app_root / "domain" / "interfaces" / "storage_provider.py",
    )

    for path in paths:
        forbidden = {
            module
            for module in _imports(path)
            if module.startswith(FORBIDDEN_IMPORT_PREFIXES)
        }
        assert forbidden == set(), f"{path.name} imports forbidden modules: {sorted(forbidden)}"
