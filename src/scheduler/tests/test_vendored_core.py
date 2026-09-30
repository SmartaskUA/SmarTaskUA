"""The scheduler's copy of the v4 domain layer must not drift from the canonical one.

The scheduler image ships src/scheduler only, so problem_v4 carries its own
copy of json_generation/schema_v4/src/schema_v4/core.py - the same arrangement
as the wizard's core.js and its parity test. If this fails, copy the canonical
file over the vendored one; never edit the copy.
"""

from conftest import SCHEDULER, SCHEMA_V4


def test_schema_core_is_byte_identical_to_the_canonical_core():
    canonical = (SCHEMA_V4 / "src" / "schema_v4" / "core.py").read_bytes()
    vendored = (SCHEDULER / "problem_v4" / "schema_core.py").read_bytes()
    assert vendored == canonical, (
        "problem_v4/schema_core.py drifted from json_generation/schema_v4/src/schema_v4/core.py; "
        "re-copy the canonical file"
    )
