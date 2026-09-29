"""`--param KEY=VALUE` parsing in the CLI."""

from scheduler.cli import _parse_key_value_pairs


def test_path_valued_params_stay_paths_even_when_the_file_exists(tmp_path):
    existing = tmp_path / "log.csv"
    existing.write_text("a,b\n1,2\n")
    parsed = _parse_key_value_pairs([
        f"results_log_file={existing}",
        f"result_dir={tmp_path}",
        "w2=1",
        "allow_day_off_swap=false",
    ])
    # an existing file would otherwise be read in and replaced by its rows
    assert parsed["results_log_file"] == str(existing)
    assert parsed["result_dir"] == str(tmp_path)
    assert parsed["w2"] == 1 and parsed["allow_day_off_swap"] is False
