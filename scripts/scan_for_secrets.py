#!/usr/bin/env python3
"""
Secret Scanner - Pre-commit Hook

Scans staged files for potential secrets before commit.
Prevents accidental exposure of API keys, passwords, and other sensitive data.

Compatible with pre-commit framework and can be run standalone.

Based on best practices from:
- GitGuardian
- detect-secrets (Yelp)
- Gitleaks patterns
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


class SecretScanner:
    """Detect potential secrets in code."""

    PATTERNS = {
        "API Key": [
            (
                r"api[_-]?key[\s]*[:=][\s]*[\"\']([^\"\']+)[\"\']",
                "API key in assignment",
            ),
            (
                r"apikey[\s]*[:=][\s]*[\"\']([^\"\']+)[\"\']",
                "API key in assignment",
            ),
        ],
        "AWS": [
            (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
            (
                r"aws[_-]?secret[_-]?access[_-]?key[\s]*[:=][\s]*[\"\']([^\"\']+)[\"\']",
                "AWS Secret Key",
            ),
        ],
        "Private Key": [
            (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "Private key file"),
        ],
        "Generic Secret": [
            (
                r"secret[\s]*[:=][\s]*[\"\']([^\"\']{8,})[\"\']",
                "Secret in assignment",
            ),
            (
                r"password[\s]*[:=][\s]*[\"\']([^\"\']{4,})[\"\']",
                "Password in assignment",
            ),
            (
                r"token[\s]*[:=][\s]*[\"\']([^\"\']{8,})[\"\']",
                "Token in assignment",
            ),
        ],
        "GitHub": [
            (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
            (
                r"github[_-]?token[\s]*[:=][\s]*[\"\']([^\"\']+)[\"\']",
                "GitHub token",
            ),
        ],
        "Slack": [
            (r"xox[baprs]-[0-9]{10,12}-[0-9]{10,12}-[a-zA-Z0-9]{24,32}", "Slack token"),
        ],
        "Google": [
            (r"AIza[0-9A-Za-z\\-_]{35}", "Google API key"),
        ],
        "Stripe": [
            (r"sk_live_[0-9a-zA-Z]{24,}", "Stripe Secret Key"),
            (r"rk_live_[0-9a-zA-Z]{24,}", "Stripe Restricted Key"),
        ],
        "JWT": [
            (r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*", "JWT token"),
        ],
        "Database": [
            (
                r"postgres://[^:]+:[^@]+@[^/]+/[^\s]+",
                "PostgreSQL connection string",
            ),
            (r"mysql://[^:]+:[^@]+@[^/]+/[^\s]+", "MySQL connection string"),
            (
                r"mongodb(\+srv)?://[^:]+:[^@]+@[^\s]+",
                "MongoDB connection string",
            ),
        ],
    }

    HIGH_ENTROPY_THRESHOLD = 4.5

    SKIP_PATTERNS = [
        r"\.git/",
        r"\.pyc$",
        r"\.egg-info/",
        r"__pycache__/",
        r"node_modules/",
        r"\.lock$",
        r"\.sum$",
        r"test[_s]/",
        r"\.md$",
    ]

    FALSE_POSITIVES = [
        "your-api-key-here",
        "your_api_key_here",
        "yourapikey",
        "YOUR_API_KEY",
        "example",
        "sample",
        "placeholder",
        "dummy",
        "test",
        "fake",
        "mock",
    ]

    def __init__(self) -> None:
        self.findings: List[Dict] = []

    def should_skip_file(self, filepath: str) -> bool:
        for pattern in self.SKIP_PATTERNS:
            if re.search(pattern, filepath):
                return True
        return False

    def is_false_positive(self, secret: str) -> bool:
        secret_lower = secret.lower()
        return any(fp in secret_lower for fp in self.FALSE_POSITIVES)

    def calculate_entropy(self, text: str) -> float:
        if not text:
            return 0.0

        entropy = 0.0
        for char in set(text):
            p_x = text.count(char) / len(text)
            if p_x > 0:
                entropy += -p_x * (p_x ** -1)

        return entropy

    def scan_file(self, filepath: Path) -> List[Dict]:
        findings: List[Dict] = []

        if self.should_skip_file(str(filepath)):
            return findings

        try:
            content = filepath.read_text(errors="ignore")
        except Exception:
            return findings

        lines = content.split("\n")

        for category, patterns in self.PATTERNS.items():
            for pattern, description in patterns:
                for line_num, line in enumerate(lines, 1):
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        secret_value = match.group(1) if match.groups() else match.group(0)

                        if self.is_false_positive(secret_value):
                            continue

                        findings.append(
                            {
                                "file": str(filepath),
                                "line": line_num,
                                "category": category,
                                "description": description,
                                "match": secret_value[:20] + "..."
                                if len(secret_value) > 20
                                else secret_value,
                                "severity": "HIGH",
                            }
                        )

        base64_pattern = r"[A-Za-z0-9+/]{30,}={0,2}"
        for line_num, line in enumerate(lines, 1):
            matches = re.finditer(base64_pattern, line)
            for match in matches:
                value = match.group(0)
                entropy = self.calculate_entropy(value)

                if entropy > self.HIGH_ENTROPY_THRESHOLD and not self.is_false_positive(value):
                    findings.append(
                        {
                            "file": str(filepath),
                            "line": line_num,
                            "category": "High Entropy",
                            "description": f"High entropy string (entropy: {entropy:.2f})",
                            "match": value[:20] + "...",
                            "severity": "MEDIUM",
                        }
                    )

        return findings

    def scan_staged_files(self) -> List[Dict]:
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                check=True,
            )

            staged_files = result.stdout.strip().split("\n")
            staged_files = [f for f in staged_files if f]

        except subprocess.CalledProcessError:
            print("Warning: Not a git repository or no staged files")
            return []

        all_findings: List[Dict] = []
        for filepath_str in staged_files:
            filepath = Path(filepath_str)
            if filepath.exists() and filepath.is_file():
                findings = self.scan_file(filepath)
                all_findings.extend(findings)

        return all_findings

    def scan_directory(self, directory: Path) -> List[Dict]:
        all_findings: List[Dict] = []

        for filepath in directory.rglob("*"):
            if filepath.is_file() and not self.should_skip_file(str(filepath)):
                findings = self.scan_file(filepath)
                all_findings.extend(findings)

        return all_findings

    def print_findings(self, findings: List[Dict]) -> None:
        if not findings:
            print("No secrets detected.")
            return

        print(f"\nFOUND {len(findings)} POTENTIAL SECRET(S):\n")
        print("=" * 70)

        for i, finding in enumerate(findings, 1):
            print(f"\n[{i}] {finding['category']} - {finding['description']}")
            print(f"    File: {finding['file']}:{finding['line']}")
            print(f"    Severity: {finding['severity']}")
            print(f"    Match: {finding['match']}")

        print("\n" + "=" * 70)
        print("\nCOMMIT BLOCKED - Remove secrets before committing!")
        print("\nIf these are false positives, you can:")
        print("  1. Use environment variables instead of hardcoded values")
        print("  2. Add to .gitignore if it's a config file")
        print("  3. Use git commit --no-verify to bypass (NOT recommended)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan for secrets in code before committing"
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Scan only staged files (default behavior)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan all files in repository",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("."),
        help="Path to scan (default: current directory)",
    )

    args = parser.parse_args()

    scanner = SecretScanner()

    if args.all:
        findings = scanner.scan_directory(args.path)
    else:
        findings = scanner.scan_staged_files()

    scanner.print_findings(findings)

    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
