# PRD

## Local Merge Validation
- Validate PR `#17` by merging it locally, reinstalling dependencies, and running repo-relevant tests before deciding whether to keep the merged result on local `main`. (Sources: CR-20260602-1105, CR-20260602-1106; D-20260602-1107)
- Keep the workflow local-only: no remote merge, no push, and no PR write actions. (Sources: CR-20260602-1105; D-20260602-1107)
- Preserve unrelated existing local files while running the validation. (Sources: CR-20260602-1105; D-20260602-1107)

## Execution Truth
- Active feature: `20260804-dependabot-security-remediation`. (Sources: CR-20260804-1352; D-20260804-1352)
- Required evidence: the open-alert inventory, repository-wide dependency usage search, a passing dependency audit, the full test suite, and the local security commit. (Sources: CR-20260804-1352; D-20260804-1352)

## Security and dependency maintenance
- Remove the direct `nltk` dependency if production and test code do not use it, so the repository no longer ships a package with unresolved Dependabot advisories. (Sources: CR-20260804-1352; D-20260804-1352)
- Require `python-dotenv` version `1.2.2` or later, the patched floor reported by Dependabot. (Sources: CR-20260804-1352; D-20260804-1352)
- Verify the remediation with an automated dependency audit and the complete repository test suite; do not dismiss or suppress alerts. (Sources: CR-20260804-1352; D-20260804-1352)

## Next / backlog
- Shipped locally on `main` via merge commit `a7625b7`: PR `#17` was merged, `requirements.txt` now allows patched `pypdf`, and ATHENA audit files were added for this validation run. Evidence: `requirements.txt`, `docs/specs/20260602-pr17-local-merge-validation/notes.md`, `docs/audit/git-history.md`. (Sources: CR-20260602-1105, CR-20260602-1106; D-20260602-1107)
- Shipped locally pending commit: removed unused NLTK, raised python-dotenv to the patched `1.2.2` floor, passed `pip-audit`, and passed all 91 tests. Evidence: `requirements.txt`, `README.md`, `docs/specs/20260804-dependabot-security-remediation/notes.md`. (Sources: CR-20260804-1352; D-20260804-1352)
