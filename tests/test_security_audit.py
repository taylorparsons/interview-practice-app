import importlib.util
import subprocess
from pathlib import Path


def load_security_auditor():
    script_path = Path("scripts/audit_repository_security.py")
    spec = importlib.util.spec_from_file_location(
        "audit_repository_security",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SecurityAuditor


def init_git_repo(repo_path: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=repo_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo_path,
        check=True,
    )


def commit_file(repo_path: Path, rel_path: str, content: str, message: str) -> None:
    file_path = repo_path / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", rel_path], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_history_scan_ignores_low_confidence_keywords(tmp_path: Path) -> None:
    security_auditor = load_security_auditor()
    init_git_repo(tmp_path)

    commit_file(
        tmp_path,
        "app/config.py",
        'api_key = "not-a-real-key"\n',
        "feat: add api key placeholder",
    )

    auditor = security_auditor(tmp_path)
    auditor.check_for_secrets_in_history()

    assert auditor.findings["critical"] == []


def test_history_scan_detects_github_pat(tmp_path: Path) -> None:
    security_auditor = load_security_auditor()
    init_git_repo(tmp_path)

    token = "ghp_" + ("a" * 36)
    commit_file(
        tmp_path,
        "app/secret.py",
        f'token = "{token}"\n',
        "feat: add token",
    )

    auditor = security_auditor(tmp_path)
    auditor.check_for_secrets_in_history()

    titles = [finding["title"] for finding in auditor.findings["critical"]]
    assert any("GitHub" in title for title in titles)


def test_sensitive_file_patterns_only_flag_secret_files(tmp_path: Path) -> None:
    security_auditor = load_security_auditor()
    init_git_repo(tmp_path)

    commit_file(
        tmp_path,
        "scripts/scan_for_secrets.py",
        "# tool\n",
        "chore: add scanner",
    )
    commit_file(
        tmp_path,
        "tests/test_scan_for_secrets.py",
        "# test\n",
        "test: add scanner test",
    )
    commit_file(
        tmp_path,
        "config/secrets.env",
        "SECRET=1\n",
        "feat: add secrets env",
    )

    auditor = security_auditor(tmp_path)
    auditor.check_sensitive_file_patterns()

    titles = [finding["title"] for finding in auditor.findings["critical"]]
    assert any("config/secrets.env" in title for title in titles)
    assert not any("scan_for_secrets.py" in title for title in titles)


def test_absolute_paths_ignores_allowlist(tmp_path: Path) -> None:
    security_auditor = load_security_auditor()
    init_git_repo(tmp_path)

    commit_file(
        tmp_path,
        ".pre-commit-config.yaml",
        "entry: /Users/example/project\n",
        "chore: add hook",
    )
    commit_file(
        tmp_path,
        "scripts/audit_repository_security.py",
        "PATH = '/Users/example/project'\n",
        "chore: add audit script",
    )
    commit_file(
        tmp_path,
        "app/main.py",
        "CONFIG = '/Users/example/project'\n",
        "feat: add app",
    )

    auditor = security_auditor(tmp_path)
    auditor.check_for_absolute_paths()

    findings = auditor.findings["high"]
    assert len(findings) == 1
    description = findings[0]["description"]
    assert "app/main.py" in description
    assert ".pre-commit-config.yaml" not in description
    assert "scripts/audit_repository_security.py" not in description
