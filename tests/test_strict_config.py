"""Projects with strict pytest settings must work without declaring the `covers` marker."""

from textwrap import dedent

from apodix.verify import PROVEN, verify


def test_strict_markers_and_warnings_as_errors(tmp_path):
    (tmp_path / "pytest.ini").write_text(dedent("""\
        [pytest]
        addopts = --strict-markers
        filterwarnings = error
    """))
    (tmp_path / "criteria.md").write_text("- R1: doubling works\n")
    (tmp_path / "lib.py").write_text("def double(x):\n    return x * 2\n")
    (tmp_path / "test_lib.py").write_text(dedent("""\
        import pytest
        from lib import double

        @pytest.mark.covers("R1")
        def test_double():
            assert double(4) == 8
    """))

    report = verify(tmp_path)

    assert report.tests_total == report.tests_passed == 1
    assert report.results[0].verdict == PROVEN
