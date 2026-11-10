# Feature Spec: 20260804-dependabot-security-remediation

Status: Done
Created: 2026-08-04 13:52
Inputs: CR-20260804-1352
Decisions: D-20260804-1352

## Summary
- Remediate the repository's 13 open Dependabot alerts by removing the unused direct NLTK dependency and upgrading python-dotenv to GitHub's patched version floor, with automated dependency-policy and regression evidence.

## User Stories & Acceptance

### US1: Remove known vulnerable direct dependencies (Priority: P1)
Narrative:
- As the repository owner, I want the reported vulnerable dependency versions removed from the manifest, so that Dependabot can close the alerts without dismissals.

Acceptance scenarios:
1. Given production and test code do not import NLTK, when the dependency manifest is patched, then NLTK is no longer declared as a direct dependency. (Verifies: FR-005)
2. Given Dependabot reports python-dotenv versions before 1.2.2 as vulnerable, when the dependency manifest is patched, then it requires python-dotenv 1.2.2 or later. (Verifies: FR-006)
3. Given the dependency patch is present, when automated validation runs, then the dependency audit and complete repository test suite pass without suppressing or dismissing alerts. (Verifies: FR-007)

## Requirements

Functional requirements:
- FR-005: Remove NLTK from direct dependencies after confirming no production or test code imports it. (Sources: CR-20260804-1352; D-20260804-1352)
- FR-006: Require python-dotenv version 1.2.2 or later in `requirements.txt`. (Sources: CR-20260804-1352; D-20260804-1352)
- FR-007: Run an automated dependency audit and the complete repository test suite before completion. (Sources: CR-20260804-1352; D-20260804-1352)

## Edge cases
- Dependabot currently labels three NLTK advisories as having no patched version; those alerts must be remediated by removing the unused package rather than by dismissal. (Verifies: FR-005, FR-007)
- If repository code imports NLTK through a path missed by the initial search, removal must stop and the dependency must be replaced or the affected feature redesigned before completion. (Verifies: FR-005)
