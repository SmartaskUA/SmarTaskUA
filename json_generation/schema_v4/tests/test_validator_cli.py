"""Loading and the JSON Schema layer -- the parts reached through `validate()`."""

from helpers import assert_isolated, dump, load, validate

def test_a_file_that_is_not_json(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{ not json", encoding="utf-8")
    assert_isolated(validate(path), "is not valid JSON")

def test_a_json_document_that_is_not_an_object(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert_isolated(validate(path), "top level must be an object")

def test_a_document_of_no_recognisable_form(tmp_path):
    path = tmp_path / "mystery.json"
    path.write_text('{"hello": "world"}', encoding="utf-8")
    assert_isolated(validate(path), "cannot tell which form this is")

def test_a_missing_file(tmp_path):
    assert_isolated(validate(tmp_path / "absent.json"), "cannot read")

def test_the_schema_layer_runs_through_the_validator(tmp_path, make_fixture):
    """Nothing else drives jsonschema via validate(), so the 'schema: ' prefix
    and the path formatting are otherwise unpinned."""
    path = make_fixture()
    doc = load(path)
    doc["metadata"]["problemId"] = 12345          # schema says string
    dump(path, doc)
    r = validate(path)
    assert any(e.startswith("schema: metadata/problemId") for e in r.errors), r.errors

def test_a_typo_inside_a_closed_object_is_caught_by_the_schema(make_fixture):
    def mutate(d):
        d["metadata"]["problemID"] = "typo"
    r = validate(make_fixture(mutate_problem=mutate))
    assert any("schema: metadata" in e for e in r.errors), r.errors

def test_a_stray_key_at_the_open_root_is_accepted(make_fixture):
    """This is what lets the templates carry _comment* keys."""
    def mutate(d):
        d["_comment_new"] = "kept"
    r = validate(make_fixture(mutate_problem=mutate))
    assert r.ok and not r.warnings, (r.errors, r.warnings)
