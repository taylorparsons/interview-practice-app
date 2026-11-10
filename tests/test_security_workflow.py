from pathlib import Path


def test_security_workflow_does_not_use_hashfiles_in_job_if() -> None:
    workflow_path = Path(".github/workflows/security.yml")
    contents = workflow_path.read_text(encoding="utf-8")

    offending_lines = [
        line
        for line in contents.splitlines()
        if line.startswith("    if:") and "hashFiles(" in line
    ]

    assert not offending_lines, (
        "hashFiles() is not allowed in job-level if expressions; "
        f"found: {offending_lines}"
    )
