"""Architectural invariants, checked by reading the imports.

The layering is the reason the validator can be lenient while the adapter is
strict without the two disagreeing about what the data says. A test is the only
thing that keeps it true.
"""

import re

from helpers import SRC

MODULES = {p.stem: p.read_text(encoding="utf-8")
           for p in (SRC / "schema_v4").glob("*.py")}


def imports_of(name: str) -> set[str]:
    src = MODULES[name]
    found = set(re.findall(r"^from \.(\w+) import", src, re.M))
    found |= {m.strip() for line in re.findall(r"^from \. import (.+)$", src, re.M)
              for m in line.split(",")}
    return found


def test_every_module_is_accounted_for():
    assert set(MODULES) == {"__init__", "core", "common", "validate_declarative",
                            "validate_result", "validator", "sisqual_adapt"}


def test_core_depends_on_nothing_in_the_package():
    assert imports_of("core") == set()


def test_no_validation_module_imports_the_adapter():
    """The validator must never silently repair what it is meant to report."""
    for name in ("core", "common", "validate_declarative", "validate_result", "validator"):
        assert "sisqual_adapt" not in imports_of(name), f"{name} imports the adapter"


def test_the_adapter_does_not_import_the_validator():
    """It converts; deciding whether the result is valid is a separate pass."""
    assert "validator" not in imports_of("sisqual_adapt")


def test_check_modules_do_not_import_each_other():
    for name in ("common", "validate_declarative", "validate_result"):
        others = {"common", "validate_declarative", "validate_result"} - {name}
        assert not (imports_of(name) & others), f"{name} reaches sideways"


def test_only_the_validator_composes_the_mixins():
    assert "CommonChecksMixin" in MODULES["validator"]
    assert "DeclarativeChecksMixin" in MODULES["validator"]
    assert "ResultChecksMixin" in MODULES["validator"]
