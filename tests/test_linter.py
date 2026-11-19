import csv
import io
from pathlib import Path

from bacnet_lint import lint_file, lint_rows
from bacnet_lint.__main__ import main
from bacnet_lint.linter import allowed_types

HEADER = "object_type,instance,name,units\n"
EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "points.csv"


def rules(body: str, **kwargs) -> list[str]:
    return [f.rule for f in lint_rows(csv.DictReader(io.StringIO(HEADER + body)), **kwargs)]


def test_clean_rows():
    assert rules("AI,1,BLDGA.AHU01.SAT,degF\nBO,2,BLDGA.AHU01.FAN_CMD,\n") == []


def test_missing_name():
    assert "B001" in rules("AI,1,,degF\n")


def test_bad_pattern():
    assert "B001" in rules("AI,1,AHU-1-SAT,degF\n")


def test_whitespace_in_name():
    assert "B002" in rules("AV,1,BLDGA.AHU01.DMPR POS,percent\n")


def test_duplicate_name_case_insensitive():
    found = rules("AI,1,BLDGA.AHU01.SAT,degF\nAI,2,bldga.ahu01.sat,degF\n")
    assert found.count("B003") == 2


def test_duplicate_object_instance():
    found = rules("AI,1,BLDGA.AHU01.SAT,degF\nAI,1,BLDGA.AHU01.RAT,degF\n")
    assert found.count("B004") == 2


def test_same_instance_different_type_is_fine():
    assert "B004" not in rules("AI,1,BLDGA.AHU01.SAT,degF\nBI,1,BLDGA.AHU01.FAN_STS,\n")


def test_unknown_object_type():
    assert "B005" in rules("XX,1,BLDGA.AHU01.SAT,degF\n")


def test_suffix_object_type_mismatch():
    assert "B006" in rules("BV,1,BLDGA.AHU01.SAT,\n")


def test_equipment_number_padding():
    assert "B007" in rules("AI,1,BLDGA.AHU1.SAT,degF\n")


def test_analog_without_units():
    assert "B008" in rules("AI,1,BLDGA.AHU01.SAT,\n")


def test_binary_without_units_is_fine():
    assert "B008" not in rules("BI,1,BLDGA.AHU01.FAN_STS,\n")


def test_name_too_long_and_limit_option():
    body = "AI,1,BLDGA.AHU01.SUPPLY_AIR_TEMP,degF\n"
    assert "B009" in rules(body, max_length=20)
    assert "B009" not in rules(body)


def test_lower_case_name():
    assert "B010" in rules("AI,1,bldga.ahu01.sat,degF\n")


def test_bad_instance_values():
    assert "B011" in rules("AI,abc,BLDGA.AHU01.SAT,degF\n")
    assert "B011" in rules("AI,4194303,BLDGA.AHU01.SAT,degF\n")
    assert "B011" not in rules("AI,4194302,BLDGA.AHU01.SAT,degF\n")


def test_allowed_types_lookup():
    assert allowed_types("SAT_SP") == {"AV", "AO"}
    assert allowed_types("FLOW") is None


def test_example_and_cli(capsys):
    assert len(lint_file(EXAMPLE)) >= 10
    assert main([str(EXAMPLE)]) == 1
    assert "finding(s)" in capsys.readouterr().out
    assert main(["nofile.csv"]) == 2
