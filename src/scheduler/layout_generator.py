from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _split_team_token(token: str) -> List[str]:
    cleaned = token.strip().upper()
    if not cleaned:
        return []

    for separator in ("+", "|", ","):
        if separator in cleaned:
            return [part.strip().upper() for part in cleaned.split(separator) if part.strip()]

    if len(cleaned) > 1 and cleaned.isalpha():
        return list(cleaned)

    return [cleaned]


def parse_layout_spec(layout_spec: str) -> Dict[str, int]:
    layout: Dict[str, int] = {}
    for item in layout_spec.split(","):
        part = item.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Invalid layout token {part!r}. Expected TEAM=COUNT.")
        team_token, count_text = part.split("=", 1)
        team_token = team_token.strip()
        count_text = count_text.strip()
        if not team_token or not count_text:
            raise ValueError(f"Invalid layout token {part!r}. Expected TEAM=COUNT.")
        try:
            count = int(count_text)
        except ValueError as exc:
            raise ValueError(f"Invalid employee count in {part!r}.") from exc
        layout[team_token] = count
    if not layout:
        raise ValueError("Layout spec is empty.")
    return layout


def build_team_layout_employees(
    layout_spec: str,
    prefix: str = "Employee",
    contract_type: str = "fullTime_8h",
    include_wrapper: bool = False,
) -> Any:
    layout = parse_layout_spec(layout_spec)
    employees: List[Dict[str, Any]] = []
    counter = 1

    for team_token, count in layout.items():
        teams = _split_team_token(team_token)
        if not teams:
            raise ValueError(f"Invalid team token {team_token!r}.")

        for _ in range(count):
            employee_name = f"{prefix} {counter}"
            employees.append(
                {
                    "id": employee_name,
                    "name": employee_name,
                    "teams": teams,
                    "contractType": contract_type,
                }
            )
            counter += 1

    if include_wrapper:
        return {
            "employees": {
                "model": "team",
                "simple": employees,
            }
        }

    return employees


def write_json_file(path: str | Path, payload: Any) -> Path:
    output_path = Path(path).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return output_path