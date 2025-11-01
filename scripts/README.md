# Automation Scripts

The utilities in this folder automate the refactoring hygiene described in the
team playbook:

- `analyze_code.py` runs static analysis over `app/` (or any subpackage) to flag
  long functions, deep nesting, and other refactoring candidates. The generated
  report is used during planning to scope work.
- `refactor_code.py` applies safe AST transformations (for example, replacing
  `== None` with `is None`) that keep style consistent before manual edits.

Both scripts are invoked from the repository root and intentionally live in
version control so contributors can extend the rule set over time.
