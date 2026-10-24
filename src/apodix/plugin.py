"""pytest plugin, loaded automatically once Apodix is installed.

- Registers the `covers` marker, so projects that use --strict-markers or
  filterwarnings = error do not need to declare it in their own config.
- While Apodix runs the tests on a changed copy of the code (APODIX_EXPECT_LOADED), it checks that the
  changed file was really imported. If the project loads that code from somewhere else, such as an
  editable install, a surviving change would prove nothing, so it prints APODIX_NOT_LOADED.
"""

import os
import sys


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "covers(*ids): link a test to the acceptance criteria it proves (Apodix)",
    )


def _same_file(a: str, b: str) -> bool:
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def pytest_sessionfinish(session, exitstatus):
    expected = os.environ.get("APODIX_EXPECT_LOADED")
    if not expected:
        return
    for module in list(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if path and _same_file(path, expected):
            return
    sys.stderr.write("\nAPODIX_NOT_LOADED\n")
