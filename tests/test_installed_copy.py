"""A project whose code is importable from elsewhere (like an editable install) must still be judged on the changed copy."""

from textwrap import dedent

from apodix.verify import PROVEN, UNPROVEN, verify


def _project(root):
    (root / "src" / "mathlib").mkdir(parents=True)
    (root / "src" / "mathlib" / "__init__.py").write_text("from .ops import double\n")
    (root / "src" / "mathlib" / "ops.py").write_text("def double(x):\n    return x * 2\n")
    (root / "tests").mkdir()
    (root / "tests" / "test_ops.py").write_text(dedent("""\
        import pytest
        from mathlib import double

        @pytest.mark.covers("R1")
        def test_double():
            assert double(4) == 8
    """))
    (root / "criteria.md").write_text("- R1: doubling works\n")


def test_changed_copy_wins_over_an_installed_copy(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    _project(project)
    # simulate `pip install -e`: the original source is importable from outside the project folder
    monkeypatch.setenv("PYTHONPATH", str(project / "src"))

    report = verify(project)

    assert report.results[0].verdict == PROVEN
    assert report.results[0].invalid == 0
    assert report.results[0].killed >= 1


def test_a_change_the_tests_never_import_is_not_counted_as_a_survivor(tmp_path):
    project = tmp_path / "proj"
    _project(project)
    # the tests always load the code from its original absolute path, which Apodix cannot override
    original = project / "src" / "mathlib"
    (project / "tests" / "conftest.py").write_text(dedent(f"""\
        import importlib.util, sys
        spec = importlib.util.spec_from_file_location(
            "mathlib", r"{original / '__init__.py'}", submodule_search_locations=[r"{original}"])
        module = importlib.util.module_from_spec(spec)
        sys.modules["mathlib"] = module
        spec.loader.exec_module(module)
    """))

    report = verify(project)

    r1 = report.results[0]
    assert r1.verdict == UNPROVEN
    assert r1.survived == []        # nothing is blamed on the tests
    assert r1.invalid >= 1
    assert "could not" in r1.reason


# ---- when the tests cannot be run, say so instead of judging them ---------------------------------

def test_a_project_with_no_runnable_tests_is_an_error_not_three_unproven(tmp_path):
    import pytest

    (tmp_path / "criteria.md").write_text("- R1: something\n")
    (tmp_path / "lib.py").write_text("def f():\n    return 1\n")
    with pytest.raises(ValueError, match="ran no tests") as error:
        verify(tmp_path)
    assert "Python used:" in str(error.value)               # tells you which interpreter was tried


def test_an_interpreter_that_cannot_start_is_reported_with_its_path(tmp_path, monkeypatch):
    import pytest

    _project(tmp_path)
    monkeypatch.setattr("apodix.runner.sys.executable", str(tmp_path / "no-such-python.exe"))
    with pytest.raises(ValueError, match="could not start"):
        verify(tmp_path)
