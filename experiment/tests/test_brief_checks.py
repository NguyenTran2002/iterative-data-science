import json

from launch.brief_checks import check_brief, check_no_data_access

COLS = {"trip_id", "fare", "tips", "trip_start_timestamp"}
GOOD = "# Brief\n\n1. How do fares vary?\n2. When do trips start?\n3. How do tips relate to fare?\n"


def tool_call(name, **inp):
    return json.dumps({"_type": "AssistantMessage", "content": [{"id": "t", "name": name, "input": inp}]})


def test_accepts_three_or_four_questions():
    assert check_brief(GOOD, COLS) == []
    assert check_brief(GOOD + "4. Which hours are busiest?\n", COLS) == []


def test_counts_headed_questions():
    text = "# Brief\n\n## How do fares vary?\n\n## When do trips start?\n\n## Do tips track the fare?\n"
    assert check_brief(text, COLS) == []


def test_rejects_two_or_five_questions_and_long_briefs():
    assert check_brief("1. a?\n2. b?\n", COLS)
    assert check_brief("".join(f"{i}. q?\n" for i in range(1, 6)), COLS)
    assert check_brief(GOOD + "word " * 400, COLS)


def test_rejects_unknown_backticked_column():
    assert check_brief(GOOD + "Use `driver_rating`.", COLS)


def test_rejects_unknown_snake_case_column():
    assert check_brief(GOOD + "Compare by driver_rating.", COLS)


def test_known_columns_and_file_names_pass():
    assert check_brief(GOOD + "Use `fare`, `tips` and trip_start_timestamp from `trips.csv`.", COLS) == []


def test_flags_data_endpoint_access(tmp_path):
    log = tmp_path / "m.jsonl"
    log.write_text(tool_call("Bash", command="curl https://data.cityofchicago.org/resource/wrvz-psew.csv") + "\n")
    assert check_no_data_access(log)


def test_reading_dataset_md_is_not_data_access(tmp_path):
    log = tmp_path / "m.jsonl"
    log.write_text(tool_call("Read", file_path="/home/analyst/work/dataset.md") + "\n"
                   + json.dumps({"_type": "ResultMessage", "result": "ok"}) + "\n")
    assert check_no_data_access(log) == []
