"""The schemas themselves: they compile, they stand alone, and they say the hard parts."""

import json

from helpers import C1, C2, load


def test_both_schemas_compile(schemas):
    assert set(schemas) == {"schema-v4-declarative.json", "schema-v4-result.json"}


def test_no_schema_references_another_file(schemas):
    for name, schema in schemas.items():
        blob = json.dumps(schema)
        for ref in ("scheduling-problem-v4.0-declarative.json",
                    "scheduling-problem-v4.0-result.json"):
            assert f'"$ref": "{ref}' not in blob, f"{name} references another schema file"
        assert '"$ref": "http' not in blob, f"{name} has a remote $ref"


def test_each_schema_validates_its_real_instance(schemas):
    from jsonschema import Draft202012Validator
    Draft202012Validator(schemas["schema-v4-declarative.json"]).validate(
        load(C2 / "problem.json"))
    Draft202012Validator(schemas["schema-v4-result.json"]).validate(
        load(C1 / "result.json"))


def test_root_is_open_but_nested_objects_are_closed(schemas):
    """The two-tier policy: _comment* keys survive, a typo inside metadata does not."""
    from jsonschema import Draft202012Validator
    schema = schemas["schema-v4-declarative.json"]
    assert "additionalProperties" not in schema
    v = Draft202012Validator(schema)

    doc = load(C2 / "problem.json")
    doc["_comment_anything"] = "kept"
    assert not list(v.iter_errors(doc))

    doc = load(C2 / "problem.json")
    doc["metadata"]["problemID"] = "typo"
    assert list(v.iter_errors(doc))


def test_declarative_documents_level_one_as_highest(schemas):
    blob = json.dumps(schemas["schema-v4-declarative.json"])
    assert "LEVEL 1 IS THE HIGHEST" in blob


def test_dimensions_is_required(schemas):
    """The whole point of v4's addition: without it nothing is checkable."""
    demand = schemas["schema-v4-declarative.json"]["$defs"]["demand"]
    assert "dimensions" in demand["required"]


def test_soft_constraints_stay_unconstrained(schemas):
    """No sample has ever populated it, so inventing a shape would be a guess."""
    soft = schemas["schema-v4-declarative.json"]["$defs"]["constraints"]["properties"]["soft"]
    assert soft["items"] == {"type": "object"}


def test_no_minitems_anywhere(schemas):
    """Empty arrays are real: contracts, competencies and soft are all legitimately []."""
    for name, schema in schemas.items():
        assert '"minItems"' not in json.dumps(schema), f"{name} forbids an empty array"
