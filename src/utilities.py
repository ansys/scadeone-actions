# Copyright (C) 2025 ANSYS, Inc. and/or its affiliates.
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

import os
import platform
from datetime import datetime
from pathlib import Path

import ansys.scadeone.core.svc.test.test_results as tr
from junitparser import Error, Failure, JUnitXml, TestCase, TestSuite


def build_failure_message(ti: tr.TestItem, failure: Failure) -> str:
    # "oracle" or "assert"
    kind = ti.kind
    parts = [
        f"Check failed {kind.name} :{ti.model_path}",
        f"cycle:{failure.cycle}",
    ]
    if kind == tr.TestItemKind.Oracle:
        # add only if available
        if getattr(failure, "actual", None) is not None:
            parts.append(f"actual:{failure.actual}")
        if getattr(failure, "expected", None) is not None:
            parts.append(f"expected:{failure.expected}")
    return " ".join(parts)


def sone2junit(sone_test_file: Path, junit_file: Path) -> str:
    """Generate JUnit XML file from the Scade One test result file"""
    # check if job result file exists
    if sone_test_file.is_file():
        # get the test name from the test result file
        sone_test_name = sone_test_file.stem
        # Parse the XML results file
        tests_results = tr.TestResultsParser.load(sone_test_file)
        # create the test suite ### the test name is not in TestResults object ###
        test_suite = TestSuite(name=sone_test_name)
        # add test cases to the suite
        tc_count = 0
        for test_case in tests_results.test_cases:
            junit_test_case: TestCase = TestCase(
                name=tc_count,
                classname=test_case.harness,
                time=(
                    datetime.strptime(test_case.end, "%Y-%m-%dT%H:%M:%S.%f")
                    - datetime.strptime(test_case.start, "%Y-%m-%dT%H:%M:%S.%f")
                ).total_seconds(),
            )
            if test_case.status == tr.TestStatus.Error:
                for ti in test_case.test_items:
                    for failure in ti.failures:
                        junit_test_case.result = [
                            Error(build_failure_message(ti, failure))
                        ]
            elif test_case.status == tr.TestStatus.Failed:
                for ti in test_case.test_items:
                    for failure in ti.failures:
                        junit_test_case.result = [
                            Failure(build_failure_message(ti, failure))
                        ]
            test_suite.add_testcase(junit_test_case)
            tc_count += 1
        # create the JUnit XML object
        junit_xml = JUnitXml()
        junit_xml.add_testsuite(test_suite)
        # save the JUnit XML file
        junit_file.parent.mkdir(parents=True, exist_ok=True)
        junit_xml.write(junit_file, pretty=True)
        message = f"JUnit XML results saved to {junit_file}"
    else:
        message = f"Error: Scade One test result file {sone_test_file} not found"
    return message


def get_windows_scade_one_install_dirs() -> list[str]:
    """Get the list of Scade One installation directories."""

    names = []
    if platform.system() == "Windows":
        import winreg as reg

        # Get Scade One installation directories from the Windows registry
        try:
            hklm = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Ansys Inc")
            for i in range(reg.QueryInfoKey(hklm)[0]):
                name = reg.EnumKey(hklm, i)
                try:
                    dir, _ = reg.QueryValueEx(
                        reg.OpenKey(hklm, r"%s\Ansys Scade One" % name), "Path"
                    )
                    names.append((name, dir))
                except FileNotFoundError:
                    pass
        except OSError:
            pass
    dirs = []
    for name, dir in sorted(names, key=lambda x: x[0]):
        dirs.append(dir)
    return dirs


def get_scade_one_home() -> str:
    """Get the Scade One home directory from environment variable or registry."""
    scade_one_home = os.getenv("SCADE_ONE_HOME")
    if scade_one_home is None:
        # If scade_one_home is not set, try to find Scade One installation directories
        dirs = get_windows_scade_one_install_dirs()
        if dirs:
            # Use the most recent Scade One installation directory
            scade_one_home = dirs[-1]
    return scade_one_home
