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

# add the path containing utilities.py
script_dir = Path(__file__).parent
sys.path.append(str(script_dir.parent.parent / "src"))


def test_returns_empty_on_non_windows(monkeypatch):
    import utilities

    # On non-Windows, the function should not try to open the registry.
    monkeypatch.setattr(utilities.platform, "system", lambda: "Linux")
    assert utilities.get_windows_scade_one_install_dirs() == []


def test_reads_registry_and_sorts_versions(monkeypatch):
    import utilities

    # Simulate Windows
    monkeypatch.setattr(utilities.platform, "system", lambda: "Windows")

    class FakeReg:
        HKEY_LOCAL_MACHINE = object()

        # Registry-like store reflecting your layout
        _store = {
            r"SOFTWARE\Ansys Inc": {
                "subkeys": ["v261", "v252"],  # intentionally unsorted
            },
            r"SOFTWARE\Ansys Inc\v261\Ansys Scade One": {
                "values": {"Path": ("C:/Program Files/ANSYS Inc/v261/Scade One", None)}
            },
            r"SOFTWARE\Ansys Inc\v252\Ansys Scade One": {
                "values": {"Path": ("C:/Program Files/ANSYS Inc/v252/Scade One", None)}
            },
        }

        @classmethod
        def OpenKey(cls, root, path):
            base = r"SOFTWARE\Ansys Inc"
            if root is cls.HKEY_LOCAL_MACHINE and path == base:
                return base  # handle
            if isinstance(root, str):  # relative from handle
                key = f"{root}\\{path}"
            else:
                key = path
            if key in cls._store:
                return key
            raise FileNotFoundError

        @classmethod
        def QueryInfoKey(cls, key):
            subkeys = cls._store[key].get("subkeys", [])
            return (len(subkeys), 0, 0)

        @classmethod
        def EnumKey(cls, key, index):
            return cls._store[key]["subkeys"][index]

        @classmethod
        def QueryValueEx(cls, key, value_name):
            return cls._store[key]["values"][value_name]

    # IMPORTANT: use monkeypatch.setitem so sys.modules is restored after the test
    monkeypatch.setitem(sys.modules, "winreg", FakeReg)

    paths = utilities.get_windows_scade_one_install_dirs()
    # Sorted lexicographically: v252 before v261
    assert paths == [
        "C:/Program Files/ANSYS Inc/v252/Scade One",
        "C:/Program Files/ANSYS Inc/v261/Scade One",
    ]


def test_ignores_version_when_product_key_missing_via_filenotfound(monkeypatch):
    import utilities

    # Covers the inner `except FileNotFoundError: pass`
    monkeypatch.setattr(utilities.platform, "system", lambda: "Windows")

    class FakeReg:
        HKEY_LOCAL_MACHINE = object()

        _store = {
            r"SOFTWARE\Ansys Inc": {"subkeys": ["v261", "v251"]},
            r"SOFTWARE\Ansys Inc\v261\Ansys Scade One": {
                "values": {"Path": ("C:/Program Files/ANSYS Inc/v261/Scade One", None)}
            },
            # v251: missing product key entirely -> OpenKey must raise FileNotFoundError
        }

        @classmethod
        def OpenKey(cls, root, path):
            base = r"SOFTWARE\Ansys Inc"
            if root is cls.HKEY_LOCAL_MACHINE and path == base:
                return base
            if isinstance(root, str):
                key = f"{root}\\{path}"
            else:
                key = path
            if key in cls._store:
                return key
            raise FileNotFoundError  # triggers the inner except

        @classmethod
        def QueryInfoKey(cls, key):
            subkeys = cls._store[key].get("subkeys", [])
            return (len(subkeys), 0, 0)

        @classmethod
        def EnumKey(cls, key, index):
            return cls._store[key]["subkeys"][index]

        @classmethod
        def QueryValueEx(cls, key, value_name):
            values = cls._store[key].get("values", {})
            if value_name not in values:
                raise FileNotFoundError  # also covered by the inner except
            return values[value_name]

    monkeypatch.setitem(sys.modules, "winreg", FakeReg)

    paths = utilities.get_windows_scade_one_install_dirs()
    assert paths == ["C:/Program Files/ANSYS Inc/v261/Scade One"]


def test_root_open_raises_oserror_returns_empty(monkeypatch):
    import utilities

    # Covers the outer `except OSError:`
    monkeypatch.setattr(utilities.platform, "system", lambda: "Windows")

    class BrokenReg:
        HKEY_LOCAL_MACHINE = object()

        @classmethod
        def OpenKey(cls, root, path):
            # Raise OSError at the very first root open
            raise OSError("Access denied")

    monkeypatch.setitem(sys.modules, "winreg", BrokenReg)

    assert utilities.get_windows_scade_one_install_dirs() == []
