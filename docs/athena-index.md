# Athena Feature Index

**Purpose**: Lightweight index to reduce token overhead by loading only active features.  
**Last updated**: 2026-08-04

## How to Use This Index

**For Athena agents**: Load this athena-index.md first. Only load specs marked as "Active" below. Skip "Archived" features unless explicitly requested by user.

**For humans**: This index shows all features. Archived features are complete and should not be modified.

---

## Active Features (Load these during sessions)

*No active features currently. All features are archived.*

---

## Archived Features (Skip unless explicitly requested)

### 20260602-pr17-local-merge-validation
- **Status**: Done
- **Spec**: docs/specs/20260602-pr17-local-merge-validation/spec.md
- **Summary**: This feature adds ATHENA traceability for a local-only validation of PR `#17`, merges the PR into an isolated branch first, verifies the `pypdf` dependency change with focused and full pytest runs, an

### 20260804-dependabot-security-remediation
- **Status**: Done
- **Spec**: docs/specs/20260804-dependabot-security-remediation/spec.md
- **Summary**: Remediate the repository's 13 open Dependabot alerts by removing the unused direct NLTK dependency and upgrading python-dotenv to GitHub's patched version floor, with automated dependency-policy and r

---

## Token Optimization

**Without athena-index.md**:
- Load all 2 specs = ~1,000 tokens

**With athena-index.md**:
- Load athena-index.md only = ~1100 tokens
- Load 0 active specs = ~0 tokens
- **Total**: ~1100 tokens
- **Savings**: ~-10% reduction

**Usage Pattern**:
1. Athena loads athena-index.md first
2. Identifies active features (currently: 0)
3. Skips 2 archived features
4. If user asks about archived feature, load on-demand
