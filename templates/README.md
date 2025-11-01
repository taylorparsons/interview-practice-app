# Code Templates

This directory hosts reusable boilerplate supplied by the refactoring toolkit.
Each template is referenced in the playbook when a cleanup calls for new
modules:

- `function_template.py`, `async_function_template.py`, and
  `class_template.py` provide docstring-heavy skeletons for quickly sketching
  helpers while documenting intent.
- `fastapi_router_template.py` captures routing patterns that align with the
  existing `app/main.py` architecture.
- `test_template.py` mirrors the repository's pytest conventions, giving
  contributors a starting point for focused regression tests.

Keeping these templates checked in makes it easy for new engineers to follow
the same structure during refactors.
