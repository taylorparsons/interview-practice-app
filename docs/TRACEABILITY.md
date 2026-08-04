# Traceability (How to follow the audit trail)

Start here:
1) Find the relevant raw requests in [docs/requests.md](docs/requests.md):
   - `CR-20260602-1105`
   - `CR-20260602-1106`
   - `CR-20260804-1352`
2) Read linked interpretations and tradeoffs in [docs/decisions.md](docs/decisions.md):
   - `D-20260602-1107`
   - `D-20260804-1352`
3) Review derived pre-ATHENA history in [docs/audit/git-history.md](docs/audit/git-history.md).
4) Open the active feature spec at [docs/specs/20260804-dependabot-security-remediation/spec.md](docs/specs/20260804-dependabot-security-remediation/spec.md).
   - Requirements use IDs (`FR-*`) and include `Sources: CR-*; D-*`.
   - Acceptance scenarios include `Verifies: FR-*`.
5) Open the feature task list at [docs/specs/20260804-dependabot-security-remediation/tasks.md](docs/specs/20260804-dependabot-security-remediation/tasks.md).
   - Tasks include `Implements: FR-*`.
6) Review execution notes in [docs/specs/20260804-dependabot-security-remediation/notes.md](docs/specs/20260804-dependabot-security-remediation/notes.md) for commands, outcomes, and completion.
