# Security Policy

## Reporting a Vulnerability

We take the security of this project seriously. If you discover a security
vulnerability, please report it responsibly.

Do not create a public GitHub issue for security vulnerabilities.

Report issues to:

- Email: security@example.com (replace with your team address)
- GitHub advisory: https://github.com/YOUR-ORG/YOUR-REPO/security/advisories/new

### What to Include

Please include:

1. Description of the vulnerability
2. Impact and severity assessment
3. Steps to reproduce
4. Proof of concept (if available)
5. Suggested fix (if you have one)
6. Contact information for follow up

### Response Timeline

- Initial response: within 48 hours
- Status update: within 7 days
- Fix timeline: depends on severity

| Severity | Response Time | Fix Timeline |
|----------|---------------|--------------|
| Critical | Immediate      | 24-48 hours  |
| High     | 24 hours       | 1 week       |
| Medium   | 48 hours       | 2-4 weeks    |
| Low      | 1 week         | As available |

---

## Supported Versions

Security fixes are provided for the latest version on the default branch.
Backports are handled on a best-effort basis.

---

## Security Practices for Contributors

### Local Checks

Run before committing:

```bash
python3 scripts/scan_for_secrets.py --staged
python3 scripts/audit_repository_security.py --quick
```

### Guidelines

- Never commit secrets, API keys, or credentials.
- Use environment variables and keep `.env` files untracked.
- Validate and sanitize user input.
- Keep dependencies up to date.
- Use HTTPS for external communication.

---

## Responsible Disclosure

- Please give us reasonable time to investigate and fix before disclosure.
- Do not access or modify data beyond what is necessary to demonstrate the issue.
- Do not perform actions that degrade availability.

---

## Contact

- Security team: security@example.com (replace with your team address)
- Security advisories: https://github.com/YOUR-ORG/YOUR-REPO/security/advisories

---

Last updated: 2025-11
