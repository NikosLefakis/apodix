"""--fail-under: a CI gate that accepts a run when enough criteria are proven."""

from pathlib import Path

import pytest

from apodix.cli import main
from apodix.verify import MISSING, PROVEN, UNPROVEN, CriterionResult, Report

DEMOS = Path(__file__).resolve().parents[1] / "demo"


def report(verdicts, tests_total=5, tests_passed=5):
    results = [CriterionResult(f"R{i}", "text", verdict, "") for i, verdict in enumerate(verdicts, 1)]
    return Report("project", "criteria.md", results, tests_total, tests_passed)


def test_default_asks_for_every_criterion_like_done():
    assert report([PROVEN, PROVEN]).meets()
    assert not report([PROVEN, UNPROVEN]).meets()
    assert report([PROVEN, PROVEN]).meets() == report([PROVEN, PROVEN]).done


def test_a_lower_bar_accepts_a_partly_proven_run():
    one_of_three = report([PROVEN, MISSING, UNPROVEN])
    assert one_of_three.meets(33)         # 1 of 3 is 33.3%
    assert not one_of_three.meets(34)
    assert report([PROVEN, PROVEN, PROVEN, UNPROVEN]).meets(75)


def test_failing_tests_always_fail_the_gate():
    assert not report([PROVEN, PROVEN], tests_total=5, tests_passed=4).meets(0)


def test_zero_percent_accepts_any_run_whose_tests_pass():
    assert report([MISSING, MISSING]).meets(0)


def test_the_share_of_proven_criteria():
    assert report([PROVEN, MISSING, UNPROVEN, UNPROVEN]).proven_share == pytest.approx(0.25)


@pytest.mark.parametrize("value, message", [
    ("-1", "must be between 0 and 100"),
    ("101", "must be between 0 and 100"),
    ("lots", "is not a number"),
])
def test_the_command_line_rejects_a_bad_value_and_says_why(value, message, capsys):
    with pytest.raises(SystemExit) as stop:
        main(["verify", str(DEMOS / "cart"), "--fail-under", value])
    assert stop.value.code == 2
    assert message in capsys.readouterr().err


def test_exit_code_follows_the_bar_on_a_real_project(capsys):
    # the cart demo proves 1 of 3 criteria, so 33% is met and 50% is not
    assert main(["verify", str(DEMOS / "cart"), "--quiet", "--no-color", "--fail-under", "33"]) == 0
    capsys.readouterr()
    assert main(["verify", str(DEMOS / "cart"), "--no-color", "--fail-under", "50"]) == 1
    assert "50% required: fail" in capsys.readouterr().err
