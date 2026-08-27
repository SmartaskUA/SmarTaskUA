"""Architecture invariants: core is standalone, the transformer and validator never
import each other (nor any validation module the transformer), and the transformer's
diagnostics and the validator's feasibility errors come from one shared scan."""
import importlib
import json

from helpers import SRC, TC

import core

# every validation module, plus the transformer, must not import the other tool
VALIDATION_MODULES = [
    "common.py", "validate_declarative.py", "validate_expanded.py",
    "validate_solution.py", "validator.py",
]


def test_core_imports_standalone():
    assert importlib.import_module("core") is not None


def test_transform_does_not_import_validator():
    src = (SRC / "transform.py").read_text()
    assert "import validator" not in src and "from validator" not in src


def test_no_validation_module_imports_transform():
    for mod in VALIDATION_MODULES:
        src = (SRC / mod).read_text()
        assert "import transform" not in src and "from transform" not in src, mod


def test_core_imports_neither_tool():
    src = (SRC / "core.py").read_text()
    assert not any(s in src for s in ("import transform", "import validator"))


def test_merge_orchestrates_above_transform_without_the_validator():
    """merge may use transform (it sits above it), but never the validator."""
    src = (SRC / "merge.py").read_text()
    assert "import transform" in src
    assert "import validator" not in src and "from validator" not in src


def test_nothing_imports_merge():
    """merge is a leaf orchestrator: core, transform and the validators ignore it."""
    for mod in ["core.py", "transform.py", *VALIDATION_MODULES]:
        src = (SRC / mod).read_text()
        assert "import merge" not in src and "from merge" not in src, mod


def test_feasibility_diagnostics_come_from_the_one_shared_scan():
    tc = json.loads((TC / "problem.json").read_text())
    assert core.scan_feasibility(tc, TC) == []
