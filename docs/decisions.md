# Decisions (append-only)

## D-20260602-1107
Date: 2026-06-02 11:07
Inputs: CR-20260602-1105, CR-20260602-1106
PRD: Local Merge Validation

Decision:
Execute PR #17 merge validation in an isolated local worktree branch first, then merge the validated result onto local `main` only if dependency installation and regression checks stay green.

Rationale:
The user asked for a local merge and test workflow, the repo lacked required ATHENA audit files, and the current checkout already had unrelated untracked docs files. A disposable worktree keeps validation isolated while still allowing the final validated merge onto local `main`.

Alternatives considered:
- Merge directly onto local `main` first (rejected because it would mix validation with unrelated local state).
- Test the PR head without a merge (rejected because the request explicitly asked for a local merge).

Acceptance / test:
- Create the isolated branch/worktree.
- Merge PR #17 there and reinstall dependencies.
- Run focused and full pytest checks before and after the merge.
- Merge the validated branch onto local `main` without pushing.

## D-20260804-1352
Date: 2026-08-04 13:52
Inputs: CR-20260804-1352
PRD: Security and dependency maintenance

Decision: Resolve alerts through dependency remediation only; do not dismiss or suppress any advisory. Upgrade required dependencies to GitHub's patched floor and remove a vulnerable direct dependency only if repository-wide inspection confirms production and test code do not import it.
Rationale: The request is to close the reported Dependabot issues, and dismissal would hide rather than remediate risk. GitHub currently reports three NLTK advisories without a patched release, so safe removal is the only dependency-level path that can close all NLTK alerts.
Alternatives considered: Upgrade NLTK to 3.10.0, which GitHub says fixes only nine alerts; dismiss the remaining alerts, which does not remediate them; replace application behavior, which is unnecessary if NLTK is unused.
