"""Per-unit-test fixtures.

Some unit tests import command submodules whose names collide with functions in
``social_research_probe.commands.__init__``. Importing the submodule rebinds
``commands.show_topics`` (etc.) from the function to the submodule object,
breaking other tests that rely on the function. The autouse fixture below
captures the original function references at collection time and restores them
before each test.
"""

from __future__ import annotations

import importlib

import pytest

import social_research_probe.commands as _commands_pkg

# Force the colliding submodules to be loaded once so the original function
# references can be re-saved after collection clobbers them.
for _sub in ("show_topics", "show_purposes", "stage_suggestions"):
    importlib.import_module(f"social_research_probe.commands.{_sub}")

# Now reload the package to recover the function bindings as written in
# __init__.py (the submodule imports overwrote them).
importlib.reload(_commands_pkg)

_ORIG = {
    "show_topics": _commands_pkg.show_topics,
    "show_purposes": _commands_pkg.show_purposes,
    "stage_suggestions": _commands_pkg.stage_suggestions,
}


@pytest.fixture(autouse=True)
def _restore_command_function_bindings():
    """Restore function references on the commands package before each test."""
    for name, fn in _ORIG.items():
        setattr(_commands_pkg, name, fn)
    yield
