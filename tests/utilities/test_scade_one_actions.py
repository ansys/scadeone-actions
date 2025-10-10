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

import platform
import sys
from argparse import ArgumentParser  # noqa: F401
from pathlib import Path
from types import SimpleNamespace

import pytest
from ansys.scadeone.core.job import JobType
from ansys.scadeone.core.scadeone import ScadeOne

# add the path containing utilities.py
script_dir = Path(__file__).parent
sys.path.append(str(script_dir.parent.parent / "src"))
import scadeone_actions as scadeone_actions  # noqa: E402

# ----------------------------- Helpers / doubles -----------------------------


class DummyProject:
    def __init__(self, jobs):
        self._jobs = {j.name: j for j in jobs}

    def load_jobs(self):
        # no-op in tests
        pass

    def get_job(self, name):
        return self._jobs.get(name)


class DummyJob:
    def __init__(
        self, name, kind, storage_root: Path, test_result_file="job_results.json"
    ):
        self.name = name
        self._kind = kind
        self.storage = SimpleNamespace(path=storage_root / "storage" / "artifact.bin")
        self.test_result_file = test_result_file
        # Prepare default "out" dir
        (storage_root / "out").mkdir(parents=True, exist_ok=True)

    def run(self):
        # Default success
        return SimpleNamespace(code=0, message=f"{self.name} OK")


# --------------------------- set_scade_one_home ------------------------------


def test_set_scade_one_home_strict_false_allows_missing_env(monkeypatch):
    # get_scade_one_home() returns None -> strict=False should not raise, scade_one_api stays None
    monkeypatch.setattr(scadeone_actions, "get_scade_one_home", lambda: None)
    actions = scadeone_actions.ScadeOneActions(scade_one_home=None)
    assert actions.scade_one_api is None  # no init performed


def test_set_scade_one_home_strict_true_raises_when_missing(monkeypatch):
    monkeypatch.setattr(scadeone_actions, "get_scade_one_home", lambda: None)
    actions = scadeone_actions.ScadeOneActions(scade_one_home=None)
    with pytest.raises(FileNotFoundError):
        actions.set_scade_one_home(None, strict=True)


def test_set_scade_one_home_with_existing_dir_initializes_api():
    """
    Provide a real install path string depending on the OS:
      - Windows: 'C:/Program Files/ANSYS Inc/v261/Scade One'
      - Linux:   '/opt/AnsysInc/v261/ScadeOne/'

    """
    is_windows = platform.system() == "Windows"
    provided_path = (
        "C:/Program Files/ANSYS Inc/v261/Scade One"
        if is_windows
        else "/opt/AnsysInc/v261/ScadeOne/"
    )

    # Run
    actions = scadeone_actions.ScadeOneActions(scade_one_home=provided_path)

    # Assert: API initialized
    assert actions.scade_one_api is not None


@pytest.mark.xfail(reason="temporarly deactivated, waiting fix #23", strict=False)
def test_set_scade_one_home_with_none_existing_dir():
    """
    Provide a wrong install path string depending on the OS:
      - Windows: 'C:/Program Files/ANSYS Inc/v261x/Scade One'
      - Linux:   '/opt/AnsysInc/v261x/ScadeOne/'

    """
    is_windows = platform.system() == "Windows"
    provided_path = (
        "C:/Program Files/ANSYS Inc/v261x/Scade One"
        if is_windows
        else "/opt/AnsysInc/v261x/ScadeOne/"
    )

    with pytest.raises(FileNotFoundError):
        actions = scadeone_actions.ScadeOneActions(  # noqa: F841
            scade_one_home=provided_path
        )


# ------------------------------- register_actions ----------------------------


def test_register_actions_registers_exactly_expected_subcommands():
    # from argparse import ArgumentParser

    import scadeone_actions

    argument_parser = ArgumentParser()
    sub = argument_parser.add_subparsers(dest="action", required=False)
    actions = scadeone_actions.ScadeOneActions(scade_one_home=None)

    # Lightweight parser used as "global_parser"
    global_parser = ArgumentParser(add_help=False)
    actions.register_actions(sub, global_parser=global_parser)

    expected = {"model_check", "code_gen", "tests_exec"}
    actual = set(sub.choices.keys())

    # Must be exactly the expected set — no extras, no missing ones
    assert (
        actual == expected
    ), f"Unexpected subcommands: {sorted(actual)} (expected {sorted(expected)})"


# ------------------------------- _get_job_type --------------------------------


def test_get_job_type_errors_when_project_missing(tmp_path):
    actions = scadeone_actions.ScadeOneActions(scade_one_home=None)
    args = SimpleNamespace(project=tmp_path / "missing.sproj", job="J")
    job, msg = actions._get_job_type(args, jobtype="ANY")
    assert job is None and "doesn't exist" in msg


def test_get_job_type_with_real_project_not_found_wrong_kind_and_ok(monkeypatch):
    # # --- prerequisites: library + project file must exist ---
    # ScadeOne_mod = pytest.importorskip("ansys.scadeone.core")
    # Job_mod = pytest.importorskip("ansys.scadeone.core.job")

    sproj = Path(__file__).parent.parent / "resources" / "Project" / "Project.sproj"
    if not sproj.is_file():
        pytest.skip(f"Project file not found at {sproj}")

    # --- prepare a real ScadeOne app (no install_dir needed for loading) ---
    # We don't rely on ScadeOneActions auto init; we inject the app instance.
    app = ScadeOne()
    actions = scadeone_actions.ScadeOneActions(scade_one_home=None)
    actions.scade_one_api = app  # give the real loader to our action object

    # Ensure jobs are loadable by the API
    project = app.load_project(sproj)
    project.load_jobs()

    # ----------------------- 1) job not found -----------------------
    args = SimpleNamespace(project=sproj, job="UnknownJobName")
    job, msg = actions._get_job_type(args, JobType.CODE_GENERATION)
    assert job is None and "not found" in msg

    # ----------------------- 2) wrong kind --------------------------
    # Use a real job name but mismatch the expected kind:
    #   CodeGenerationJob exists but we ask for MODEL_CHECK
    args = SimpleNamespace(project=sproj, job="CodeGenerationJob")
    job, msg = actions._get_job_type(args, JobType.MODEL_CHECK)
    assert job is None and "is not a" in msg

    # ----------------------- 3) correct kind ------------------------
    # ModelCheckJob exists and is of type MODEL_CHECK
    args = SimpleNamespace(project=sproj, job="ModelCheckJob")
    job, msg = actions._get_job_type(args, JobType.MODEL_CHECK)
    assert job is not None and "found in project" in msg

    # As an extra check, verify the TestExecution job too
    args = SimpleNamespace(project=sproj, job="TestExecutionJob1")
    job, msg = actions._get_job_type(args, JobType.TEST_EXECUTION)
    assert job is not None and "found in project" in msg


# -------------------------------- action_code_gen -----------------------------


def test_action_code_gen_success_with_output():
    from ansys.scadeone.core.svc.generated_code import GeneratedCode

    sproj = Path(__file__).parent.parent / "resources" / "Project" / "Project.sproj"
    if not sproj.is_file():
        pytest.skip(f"Project file not found at {sproj}")
    is_windows = platform.system() == "Windows"
    provided_path = (
        "C:/Program Files/ANSYS Inc/v261/Scade One"
        if is_windows
        else "/opt/AnsysInc/v261/ScadeOne/"
    )

    # Run code generation action
    scadeone_actions.scadeone_actions(
        [
            "code_gen",
            "-s",
            provided_path,
            "-p",
            str(sproj),
            "-j",
            "CodeGenerationJob",
            "-o",
            "tests/unit_tests_out_gen",
        ]
    )

    # Load the project to access to the generated code
    app = ScadeOne()
    project = app.load_project(str(sproj))
    code_gen = GeneratedCode(project, "CodeGenerationJob")

    # To check that the job has been executed
    assert code_gen.is_code_generated
