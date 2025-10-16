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

import pytest

# add the path containing utilities.py
script_dir = Path(__file__).parent
sys.path.append(str(script_dir.parent.parent / "src"))


@pytest.mark.parametrize(
    "json_in",
    [
        (
            Path(__file__).parent.parent
            / "resources"
            / "Json"
            / "testResultsPassed.json"
        ),  # test passed
        (
            Path(__file__).parent.parent
            / "resources"
            / "Json"
            / "testResultsOracleError.json"
        ),  # test error
        (
            Path(__file__).parent.parent
            / "resources"
            / "Json"
            / "testResultsAssertFailed.json"
        ),  # test failed
    ],
    ids=["test_passed", "test_error", "test_failed"],
)
def test_sone2junit(json_in, request, tmp_path):
    import utilities

    case_id = request.node.callspec.id
    junit_out = tmp_path / "unit_tests_out_gen" / f"test_result_{case_id}.xml"

    msg = utilities.sone2junit(json_in, junit_out)

    assert isinstance(msg, str) and msg.strip() != ""
    assert junit_out.exists()


def test_sone2junit_when_input_missing(tmp_path: Path):
    import utilities

    """If the input file does not exist, the function should not create output."""
    missing = tmp_path / "does_not_exist.json"
    junit_out = tmp_path / "unit_tests_out_gen" / "results.xml"

    msg = utilities.sone2junit(missing, junit_out)

    # Be tolerant about the exact message, but assert it's a string and no file was written.
    assert isinstance(msg, str) and msg.strip() != ""
    assert not junit_out.exists()
