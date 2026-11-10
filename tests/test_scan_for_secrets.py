import importlib.util
from pathlib import Path


def load_secret_scanner_class():
    script_path = Path("scripts/scan_for_secrets.py")
    spec = importlib.util.spec_from_file_location("scan_for_secrets", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SecretScanner


def test_scan_for_secrets_skips_self_file() -> None:
    secret_scanner_class = load_secret_scanner_class()
    scanner = secret_scanner_class()

    findings = scanner.scan_file(Path("scripts/scan_for_secrets.py"))

    assert findings == []


def test_scan_for_secrets_skips_venv_files(tmp_path: Path) -> None:
    secret_scanner_class = load_secret_scanner_class()
    scanner = secret_scanner_class()

    venv_file = tmp_path / "venv" / "lib" / "python3.11" / "site-packages" / "example.py"
    venv_file.parent.mkdir(parents=True, exist_ok=True)
    venv_file.write_text('DATABASE_URL="postgres://user:pass@localhost/db"')

    findings = scanner.scan_file(venv_file)

    assert findings == []
