"""The agenda is referenced from code, templates and every README.

Those references are ordinal, and the agenda gets renumbered whenever an item is
inserted -- which has already silently broken five of them once. Each reference
therefore carries an anchor phrase, and this file checks that the number and the
phrase still agree.
"""

import re

import pytest
from helpers import V4

AGENDA = V4 / "next_meeting.md"
#: `... item 7 ("Two contracts can be identical")` or `... item 7 (no quotes)`
REF = re.compile(r"next_meeting\.md[^\n]{0,20}?item (\d+)"
                 r"(?:\s*\(\s*[\\\"']*([^\"')\\]+)[\\\"']*\s*\))?")
SKIP = {".venv", "reference", "__pycache__", ".pytest_cache", ".git"}


def flatten(text: str) -> str:
    """Strip the markdown an anchor phrase will not have: backticks, emphasis,
    and the line wrapping that can split a phrase across two lines."""
    return re.sub(r"\s+", " ", re.sub(r"[`*_]", "", text)).lower()


def agenda_items() -> dict[int, str]:
    """{number: the item's full text} from the agenda's numbered headings."""
    text = AGENDA.read_text(encoding="utf-8")
    starts = [(int(m.group(1)), m.start()) for m in re.finditer(r"^\*\*(\d+)\. ", text, re.M)]
    items = {}
    for (n, a), (_, b) in zip(starts, starts[1:] + [(None, len(text))]):
        items[n] = text[a:b]
    return items


def references():
    for path in sorted(V4.rglob("*")):
        if not path.is_file() or any(part in SKIP for part in path.parts):
            continue
        if path.suffix not in (".py", ".md", ".csv", ".json") or path == AGENDA:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for m in REF.finditer(text):
            yield path.relative_to(V4), int(m.group(1)), (m.group(2) or "").strip()


def test_the_agenda_is_numbered_from_one_without_gaps():
    nums = sorted(agenda_items())
    assert nums == list(range(1, len(nums) + 1)), nums


def test_there_are_references_to_check():
    assert list(references()), "the guard below would be vacuous"


@pytest.mark.parametrize("path, number, anchor",
                         list(references()),
                         ids=lambda v: str(v) if not isinstance(v, str) else v[:24])
def test_every_agenda_reference_resolves(path, number, anchor):
    items = agenda_items()
    assert number in items, f"{path} points at item {number}; the agenda has {len(items)}"
    assert anchor, f"{path} cites item {number} with no anchor phrase -- add one"
    assert flatten(anchor) in flatten(items[number]), (
        f"{path} cites item {number} as {anchor!r}, but that item says:\n"
        f"{items[number][:160]}")


def test_every_agenda_item_number_is_cited_or_deliberately_not():
    """Not a failure -- a reminder of which items nothing points at."""
    cited = {n for _, n, _ in references()}
    uncited = sorted(set(agenda_items()) - cited)
    assert len(uncited) < len(agenda_items()), "nothing references the agenda at all"
