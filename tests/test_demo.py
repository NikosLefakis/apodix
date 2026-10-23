"""End to end: Apodix against the two cart demos."""

from pathlib import Path

import pytest

from apodix.cli import main
from apodix.verify import MISSING, PROVEN, UNPROVEN, verify

DEMOS = Path(__file__).resolve().parents[1] / "demo"


@pytest.fixture(scope="module")
def broken():
    return verify(DEMOS / "cart")


@pytest.fixture(scope="module")
def fixed():
    return verify(DEMOS / "cart_fixed")


def test_agent_claims_done_but_only_one_criterion_is_proven(broken):
    assert broken.tests_total == broken.tests_passed == 12  # all green, yet...
    assert [r.verdict for r in broken.results] == [PROVEN, MISSING, UNPROVEN]
    assert not broken.done


def test_the_weak_test_is_unproven_because_mutants_survived(broken):
    r3 = broken.results[2]
    assert r3.tests == ["test_empty_code"]
    assert r3.killed < r3.total
    assert r3.survived


def test_missing_criterion_names_the_marker_to_add(broken):
    assert 'covers("R2")' in broken.results[1].reason


def test_after_the_gaps_are_fixed_everything_is_proven(fixed):
    assert [r.verdict for r in fixed.results] == [PROVEN, PROVEN, PROVEN]
    assert fixed.done


def test_exit_code_is_nonzero_until_done(capsys):
    assert main(["verify", str(DEMOS / "cart"), "--quiet", "--no-color"]) == 1
    assert main(["verify", str(DEMOS / "cart_fixed"), "--quiet", "--no-color"]) == 0
    capsys.readouterr()
