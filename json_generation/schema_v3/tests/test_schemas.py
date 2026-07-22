"""The three form schemas: they compile, stand alone, validate real instances, and
agree on the competence-level polarity."""
import json

from helpers import SIS
from jsonschema import Draft202012Validator


def test_all_three_schemas_compile(schemas):
    assert set(schemas) == {
        "schema-v3-declarative.json",
        "schema-v3-expanded.json",
        "schema-v3-solution.json",
    }


def test_no_schema_references_another_file(schemas):
    # Each schema is standalone; no registry needed.
    assert not any("common.json" in json.dumps(d) for d in schemas.values())


def test_standalone_schema_validates_real_instances(schemas):
    for form, f, name in [
        ("declarative", "schema-v3-declarative.json", "problem.json"),
        ("expanded", "schema-v3-expanded.json", "problem.expanded.json"),
    ]:
        inst = json.loads((SIS / name).read_text())
        errs = list(Draft202012Validator(schemas[f]).iter_errors(inst))
        assert not errs, str(errs[:1])


def test_both_schemas_document_level_one_as_highest(schemas):
    def one_is_highest(schema):
        d = schema["$defs"]["competenceLevel"]["description"].lower()
        return "1 is the highest" in d and "junior" not in d

    assert all(one_is_highest(schemas[f]) for f in
               ("schema-v3-declarative.json", "schema-v3-expanded.json"))


def test_competence_level_copies_identical(schemas):
    assert (schemas["schema-v3-declarative.json"]["$defs"]["competenceLevel"]
            == schemas["schema-v3-expanded.json"]["$defs"]["competenceLevel"])
