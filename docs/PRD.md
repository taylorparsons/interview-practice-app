# PRD

## Local Merge Validation
- Validate PR `#17` by merging it locally, reinstalling dependencies, and running repo-relevant tests before deciding whether to keep the merged result on local `main`. (Sources: CR-20260602-1105, CR-20260602-1106; D-20260602-1107)
- Keep the workflow local-only: no remote merge, no push, and no PR write actions. (Sources: CR-20260602-1105; D-20260602-1107)
- Preserve unrelated existing local files while running the validation. (Sources: CR-20260602-1105; D-20260602-1107)

## Execution Truth
- Active feature: `20260602-pr17-local-merge-validation`. (Sources: CR-20260602-1106; D-20260602-1107)
- Required evidence: baseline test results, post-merge test results, installed `pypdf` version, and the local merge commit(s). (Sources: CR-20260602-1105, CR-20260602-1106; D-20260602-1107)

## Next / backlog
- Shipped locally on `main` via merge commit `a7625b7`: PR `#17` was merged, `requirements.txt` now allows patched `pypdf`, and ATHENA audit files were added for this validation run. Evidence: `requirements.txt`, `docs/progress.txt`, `docs/audit/git-history.md`. (Sources: CR-20260602-1105, CR-20260602-1106; D-20260602-1107)
