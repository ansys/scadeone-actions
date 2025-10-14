# Copyright (C) 2024 - 2025 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
from pathlib import Path

from pytest import MonkeyPatch

# add the path containing utilities.py
script_dir = Path(__file__).parent
sys.path.append(str(script_dir.parent.parent / "src"))

# ---------- Stubs to isolate external deps (parser + junitparser) ----------


class StubTestCaseObj:
    """Minimal representation of a Scade One test case."""

    def __init__(self, harness, start, end, status):
        self.harness = harness
        self.start = start  # "%Y-%m-%dT%H:%M:%S.%f"
        self.end = end
        self.status = status  # "passed" | "failed" | "error"


class StubJUnitTestCase:
    """Replacement for junitparser.TestCase."""

    def __init__(self, name, classname=None, time=None):
        self.name = name
        self.classname = classname
        self.time = time
        self._error = False
        self._failed = False

    def add_error(self, _err):
        self._error = True

    def add_failure(self, _sk):
        self._failed = True


class StubTestSuite:
    """Replacement for junitparser.TestSuite."""

    def __init__(self, name):
        self.name = name
        self.testcases = []

    def add_testcase(self, tc):
        self.testcases.append(tc)


class StubJUnitXml:
    """Replacement for junitparser.JUnitXml that records calls."""

    last_added_suite = None
    last_write_dest = None
    last_pretty = None

    def add_testsuite(self, suite):
        StubJUnitXml.last_added_suite = suite

    def write(self, dest, pretty=True):
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("<testsuites/>")
        StubJUnitXml.last_write_dest = str(dest)
        StubJUnitXml.last_pretty = pretty


class _Marker:  # stand-in for junitparser.Error/Skipped
    pass


# ------------------------------ Tests ----------------------------------


def test_returns_message_and_no_output_when_input_missing(tmp_path: Path):
    import utilities

    """If the input file does not exist, the function should not create output."""
    missing = tmp_path / "does_not_exist.json"
    junit_out = tmp_path / "out" / "results.xml"

    msg = utilities.sone2junit(missing, junit_out)

    # Be tolerant about the exact message, but assert it's a string and no file was written.
    assert isinstance(msg, str) and msg.strip() != ""
    assert not junit_out.exists()


def test_writes_junit(monkeypatch: MonkeyPatch, tmp_path: Path):
    import utilities

    """Happy path: parses 3 cases (Pass/Fail/Error), maps to JUnit, and writes a file."""
    # 1) Provide a real (dummy) input file so is_file() passes.
    sone_in = tmp_path / "job_results.json"
    sone_in.write_text("{}")
    junit_out = tmp_path / "junit" / "results.xml"

    # 2) Mock the Scade One parser to return deterministic test cases.
    fake_cases = [
        StubTestCaseObj(
            harness="QuadTest::TestVerticalAccel",
            start="2025-10-07T15:47:58.713",
            end="2025-10-07T15:47:58.713",
            status="passed",
        ),
        StubTestCaseObj(
            harness="QuadTest::TestRightRoll",
            start="2025-10-07T15:47:58.713",
            end="2025-10-07T15:47:58.713",
            status="error",
        ),
        StubTestCaseObj(
            harness="QuadTest::TestExeVerticalAccem",
            start="2025-10-07T15:47:58.713",
            end="2025-10-07T15:47:58.713",
            status="failed",
        ),
    ]
    monkeypatch.setattr(
        utilities.TestResultsParser,
        "load",
        lambda p: type("R", (), {"test_cases": fake_cases}),
    )

    # 3) Mock junitparser symbols used by sone2junit.
    monkeypatch.setattr(utilities, "TestCase", StubJUnitTestCase)
    monkeypatch.setattr(utilities, "TestSuite", StubTestSuite)
    monkeypatch.setattr(utilities, "JUnitXml", StubJUnitXml)
    monkeypatch.setattr(utilities, "Error", _Marker)
    monkeypatch.setattr(utilities, "Failure", _Marker)

    # 4) Call the function under test.
    msg = utilities.sone2junit(sone_in, junit_out)

    # 5) Verify a file was written and junit "write" was called.
    assert junit_out.exists()
    assert isinstance(msg, str) and msg.strip() != ""
    assert StubJUnitXml.last_write_dest == str(junit_out)

    # 6) Inspect the produced suite and its testcases.
    suite = StubJUnitXml.last_added_suite
    assert isinstance(suite, StubTestSuite)
    assert len(suite.testcases) == 3

    tc0, tc1, tc2 = suite.testcases

    # Status mapping: failed -> failure, error -> error
    assert tc1._error is True
    assert tc2._failed is True

    # Classnames should carry the harness name
    assert tc0.classname == "QuadTest::TestVerticalAccel"
    assert tc1.classname == "QuadTest::TestRightRoll"
    assert tc2.classname == "QuadTest::TestExeVerticalAccem"
