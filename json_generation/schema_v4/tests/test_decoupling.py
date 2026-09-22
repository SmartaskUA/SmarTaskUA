"""Architectural invariants, checked by reading the imports.

The layering is why the validator can be lenient while the domain layer is
strict without the two disagreeing about what the data says. A test is the only
thing that keeps it true.
"""

import re

from helpers import SRC

MODULES = {p.stem: p.read_text(encoding="utf-8")
           for p in (SRC / "schema_v4").glob("*.py")}

CHECKERS = {"validate_input", "validate_result"}


def imports_of(name: str) -> set[str]:
    src = MODULES[name]
    found = set(re.findall(r"^from \.(\w+) import", src, re.M))
    found |= {m.strip() for line in re.findall(r"^from \. import (.+)$", src, re.M)
              for m in line.split(",")}
    return found


def test_every_module_is_accounted_for():
    assert set(MODULES) == {"__init__", "core", "common", "validate_input",
                            "validate_result", "validator", "build_example_result"}


def test_the_adapter_is_gone():
    """Deleted on purpose: the schema is the deliverable, and an adapter for a
    format Sisqual has not agreed to would be built against a moving target."""
    assert "sisqual_adapt" not in MODULES
    for name, src in MODULES.items():
        assert "sisqual_adapt" not in src, f"{name} still names the adapter"


def test_core_depends_on_nothing_in_the_package():
    assert imports_of("core") == set()


def test_the_two_form_checkers_do_not_import_each_other():
    """They are peers. Anything they share belongs in common, below both."""
    for name in CHECKERS:
        assert not (imports_of(name) & (CHECKERS - {name})), f"{name} reaches sideways"


def test_common_sits_below_both_checkers_and_not_beside_them():
    assert "common" in imports_of("validate_input")
    assert "common" in imports_of("validate_result")
    assert not (imports_of("common") & (CHECKERS | {"validator", "build_example_result"}))


def test_the_generator_is_a_leaf():
    """It builds an example; deciding whether the example is valid is a separate
    pass, so it must not reach into the validator."""
    assert imports_of("build_example_result") <= {"core"}
    for name in MODULES:
        if name != "build_example_result":
            assert "build_example_result" not in imports_of(name)


def test_no_lazy_import_smuggles_a_dependency_past_the_guard():
    """imports_of anchors on ^from ., so an indented import would be invisible."""
    for name, src in MODULES.items():
        assert not re.search(r"^[ \t]+from \.\w+ import", src, re.M), \
            f"{name} has a function-local package import"


def test_only_the_validator_composes_the_mixins():
    from schema_v4.common import CommonChecksMixin
    from schema_v4.validate_input import InputChecksMixin
    from schema_v4.validate_result import ResultChecksMixin
    from schema_v4.validator import SchemaValidator
    for mixin in (CommonChecksMixin, InputChecksMixin, ResultChecksMixin):
        assert issubclass(SchemaValidator, mixin)
