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
    assert check_brief(GOOD + "word " * 500, COLS)
    assert check_brief(GOOD + "word " * 450, COLS) == []


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


def test_flags_any_portal_or_dataset_mention(tmp_path):
    for call in (tool_call("Bash", command="curl https://data.cityofchicago.org/api/v3/views/wrvz-psew/query.json"),
                 tool_call("Bash", command="python fetch.py --dataset wrvz-psew")):
        log = tmp_path / "m.jsonl"
        log.write_text(call + "\n")
        assert check_no_data_access(log)


def test_numbered_items_without_a_question_mark_are_not_questions():
    deliverables = "\n## Deliverables\n\n1. **A notebook**\n2. **A summary**\n3. **Charts**\n"
    assert check_brief(GOOD + deliverables, COLS) == []
    headed = "### 1. When do trips start?\n### 2. Where?\n### 3. Who pays?\n### 4. How much?\n"
    assert check_brief(headed + deliverables, COLS) == []


def test_writer_files_say_nothing_about_the_skill_or_how_to_work():
    from pathlib import Path
    prompts = Path(__file__).parents[1] / "prompts"
    for name in ("task_writer.md", "environment.md"):
        text = (prompts / name).read_text().lower()
        for word in ("iterative", "skill", "claude", "agent", "verify", "check each", "batch"):
            assert word not in text, (name, word)


def test_writer_is_told_the_limits_it_is_checked_against():
    from pathlib import Path
    text = (Path(__file__).parents[1] / "prompts/task_writer.md").read_text()
    assert "three or four" in text and "under 500 words" in text and "environment.md" in text
