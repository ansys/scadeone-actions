# Copyright (C) 2024 - 2026 ANSYS, Inc. and/or its affiliates.
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
sys.path.append(str(script_dir.parent.parent / "python-scripts"))


@pytest.mark.parametrize(
    "scade_one_dir",
    ["/opt/AnsysInc/v261/ScadeOne/", "C:/Program Files/ANSYS Inc/v261/Scade One"],
)
def test_prefers_env_variable(monkeypatch, scade_one_dir):
    import utilities

    # If the environment variable is set, it must take precedence.
    monkeypatch.setenv("SCADE_ONE_HOME", scade_one_dir)
    assert utilities.get_scade_one_home() == scade_one_dir


def test_fallback_to_latest_install_dir(monkeypatch):
    import utilities

    # If the env var is not set, fall back to the latest directory
    # returned by the helper (assumed to be the last element).
    monkeypatch.delenv("SCADE_ONE_HOME", raising=False)
    monkeypatch.setattr(
        utilities,
        "get_windows_scade_one_install_dirs",
        lambda: [
            "C:/Program Files/ANSYS Inc/v252/Scade One",
            "C:/Program Files/ANSYS Inc/v261/Scade One",
        ],
    )
    assert utilities.get_scade_one_home() == "C:/Program Files/ANSYS Inc/v261/Scade One"


def test_returns_none_when_not_found(monkeypatch):
    import utilities

    # If neither the env var nor any install directory is available, return None.
    monkeypatch.delenv("SCADE_ONE_HOME", raising=False)
    monkeypatch.setattr(utilities, "get_windows_scade_one_install_dirs", lambda: [])
    assert utilities.get_scade_one_home() is None
