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

is_windows = platform.system() == "Windows"
scade_home_dir = (
    "C:/Program Files/ANSYS Inc/v261/Scade One"
    if is_windows
    else "/opt/AnsysInc/v261/ScadeOne/"
)
wrong_scade_home_dir = (
    "C:/Program Files/ANSYS Inc/v261x/Scade One"
    if is_windows
    else "/opt/AnsysInc/v261x/ScadeOne/"
)

sproj = Path(__file__).parent.parent / "resources" / "Project" / "Project.sproj"

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


def test_scade_one_home_none_get_scade_one_home_none(monkeypatch):
    """When no path is provided and discovery returns None, raise FileNotFoundError."""

    monkeypatch.setattr(scadeone_actions, "get_scade_one_home", lambda: None)

    with pytest.raises(FileNotFoundError) as ei:
        scadeone_actions.ScadeOneActions(scade_one_home=None)
    assert "Scade One home directory not found" in str(ei.value)


def test_scade_one_home_none_and_nonexistent_dir(monkeypatch, tmp_path):
    """When discovery returns a non-existent directory, raise FileNotFoundError."""
    missing = tmp_path / "does_not_exist"
    monkeypatch.setattr(scadeone_actions, "get_scade_one_home", lambda: str(missing))

    with pytest.raises(FileNotFoundError) as ei:
        scadeone_actions.ScadeOneActions(scade_one_home=None)

    assert "No Scade One installation directory found" in str(ei.value)


def test_set_scade_one_home_with_existing_dir_initializes_api():
    """
    Provide a real install path string depending on the OS:
      - Windows: 'C:/Program Files/ANSYS Inc/v261/Scade One'
      - Linux:   '/opt/AnsysInc/v261/ScadeOne/'

    """

    # Run
    actions = scadeone_actions.ScadeOneActions(scade_one_home=scade_home_dir)

    # Assert: API initialized
    assert actions.scade_one_api is not None


def test_set_scade_one_home_with_none_existing_dir():
    """
    Provide a wrong install path string depending on the OS:
      - Windows: 'C:/Program Files/ANSYS Inc/v261x/Scade One'
      - Linux:   '/opt/AnsysInc/v261x/ScadeOne/'

    """

    with pytest.raises(FileNotFoundError):
        actions = scadeone_actions.ScadeOneActions(  # noqa: F841
            scade_one_home=wrong_scade_home_dir
        )


# ------------------------------- register_actions ----------------------------


def test_register_actions_registers_exactly_expected_subcommands():
    # from argparse import ArgumentParser

    import scadeone_actions

    argument_parser = ArgumentParser()
    sub = argument_parser.add_subparsers(dest="action", required=False)
    actions = scadeone_actions.ScadeOneActions(scade_one_home=scade_home_dir)

    # Lightweight parser used as "global_parser"
    global_parser = ArgumentParser(add_help=False)
    actions.register_actions(sub, global_parser=global_parser)

    expected = {"model_check", "code_gen", "tests_exec", "fmu_export", "simulation"}
    actual = set(sub.choices.keys())

    # Must be exactly the expected set — no extras, no missing ones
    assert (
        actual == expected
    ), f"Unexpected subcommands: {sorted(actual)} (expected {sorted(expected)})"


# ------------------------------- _get_job_type --------------------------------


def test_get_job_type_errors_when_project_missing(tmp_path):
    actions = scadeone_actions.ScadeOneActions(scade_one_home=scade_home_dir)
    args = SimpleNamespace(project=tmp_path / "missing.sproj", job="J")
    job, msg = actions._get_job_type(args, jobtype="ANY")
    assert job is None and "doesn't exist" in msg


@pytest.mark.parametrize(
    "job_name, expected_type, is_none, text",
    [
        # not found
        ("UnknownJobName", JobType.CODE_GENERATION, True, "not found"),
        # wrong kind (CodeGenerationJob exists but we expect MODEL_CHECK)
        ("CodeGenerationJob", JobType.MODEL_CHECK, True, "is not a"),
        # correct kind (ModelCheckJob is MODEL_CHECK)
        ("ModelCheckJob", JobType.MODEL_CHECK, False, "found in project"),
        # extra: TestExecution job correct
        ("TestExecutionJob1", JobType.TEST_EXECUTION, False, "found in project"),
    ],
    ids=["not_found", "wrong_kind", "model_check_ok", "test_exec_ok"],
)
def test_get_job_type_parametrized(job_name, expected_type, is_none, text):
    # # --- prerequisites: library + project file must exist ---
    # ScadeOne_mod = pytest.importorskip("ansys.scadeone.core")
    # Job_mod = pytest.importorskip("ansys.scadeone.core.job")

    # --- prepare a real ScadeOne app (no install_dir needed for loading) ---
    # We don't rely on ScadeOneActions auto init; we inject the app instance.
    app = ScadeOne()
    actions = scadeone_actions.ScadeOneActions(scade_one_home=scade_home_dir)
    actions.scade_one_api = app  # give the real loader to our action object

    # Ensure jobs are loadable by the API
    project = app.load_project(sproj)
    project.load_jobs()

    args = SimpleNamespace(project=sproj, job=job_name)
    job, msg = actions._get_job_type(args, jobtype=expected_type)

    if is_none:
        assert job is None, f"Expected None for job {job_name}"
    else:
        assert job is not None, f"Expected a job instance for {job_name}"

    assert text in msg, f"Expected '{text}' in message, got: {msg}"


# --- scadeone_actions() success tests ------------------------------------------
# --- Parametrized CLI  ---------------------------------------------------------


@pytest.mark.parametrize(
    "action, job_name, out_kind",
    [
        ("code_gen", "CodeGenerationJob", "dir"),  # needs an output directory (-o)
        ("tests_exec", "TestExecutionJob1", "junit"),  # needs a junit file (--junit)
        ("model_check", "ModelCheckJob", "file"),  # needs an output file (-o)
        (
            "fmu_export",
            "CodeGenerationJob",
            "fmu_ME",
        ),  # needs an output dir (-o) and kind (-k ME/CS)
        (
            "fmu_export",
            "CodeGenerationJob",
            "fmu_CS",
        ),  # needs an output dir (-o) and kind (-k ME/CS)
        ("simulation", "SimulationJob", "dir"),  # needs an output directory (-o)
    ],
    ids=[
        "code_gen",
        "tests_exec",
        "model_check",
        "fmu_export_ME",
        "fmu_export_CS",
        "simulation",
    ],
)
@pytest.mark.skipif(not is_windows, reason="FMU export is only supported on Windows.")
def test_scadeone_actions_success(action, job_name, out_kind, tmp_path):
    """
    Single parametrized test covering the 3  actions.
    It asserts the scadeone_action returns 0. Outputs are written into tmp_path.
    """
    # Build action-specific extra args, all under tmp_path to avoid repo writes
    if out_kind == "dir":
        out = tmp_path / "unit_tests_out_gen"
        extra = ["-o", str(out)]
    elif out_kind == "junit":
        out = tmp_path / "unit_tests_out_gen" / "tests_exec_report.xml"
        out.parent.mkdir(parents=True, exist_ok=True)
        extra = ["--junit", str(out)]
    elif out_kind == "file":
        out = tmp_path / "unit_tests_out_gen" / "model_check_report.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        extra = ["-o", str(out)]
    elif out_kind == "fmu_ME":
        out = tmp_path / "unit_tests_out_gen" / "exported_model_ME"
        out.parent.mkdir(parents=True, exist_ok=True)
        extra = ["-o", str(out)]
        extra += ["-k", "ME"]  # FMU export flag
    elif out_kind == "fmu_CS":
        out = tmp_path / "unit_tests_out_gen" / "exported_model_CS"
        out.parent.mkdir(parents=True, exist_ok=True)
        extra = ["-o", str(out)]
        extra += ["-k", "CS"]  # FMU export flag
    else:
        raise RuntimeError("Unsupported out_kind in parametrization")

    actions = scadeone_actions.scadeone_actions(
        [
            action,
            "-s",
            scade_home_dir,
            "-p",
            str(sproj),
            "-j",
            job_name,
            *extra,
        ]
    )

    assert actions == 0


# --- scadeone_actions() fail  tests ------------------------------------------
# --- Parametrized CLI  ---------------------------------------------------------
@pytest.mark.parametrize(
    "action, job_name, out_kind",
    [
        # Wrong kind: ask code_gen to run a ModelCheck job
        ("code_gen", "ModelCheckJob", "dir"),
        # Job not found (typo/unknown)
        ("tests_exec", "TestExecutionJob51", "junit"),
        ("model_check", "ModelCheckJob13", "file"),
    ],
    ids=[
        "code_gen_wrong_kind",
        "tests_exec_job_not_found",
        "model_check_job_not_found",
    ],
)
def test_scadeone_actions_failed(action, job_name, out_kind, tmp_path):
    """
    Negative CLI tests: each scenario must return actions=2.
    Outputs are directed under tmp_path to avoid repo writes.
    """
    if out_kind == "dir":
        out = tmp_path / "unit_tests_out_fail" / "gen_dir"
        extra = ["-o", str(out)]
    elif out_kind == "junit":
        out = tmp_path / "unit_tests_out_fail" / "tests_exec_report.xml"
        out.parent.mkdir(parents=True, exist_ok=True)
        extra = ["--junit", str(out)]
    elif out_kind == "file":
        out = tmp_path / "unit_tests_out_fail" / "model_check_report.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        extra = ["-o", str(out)]
    else:
        raise RuntimeError("Unsupported out_kind in parametrization")

    actions = scadeone_actions.scadeone_actions(
        [
            action,
            "-s",
            scade_home_dir,
            "-p",
            str(sproj),
            "-j",
            job_name,
            *extra,
        ]
    )
    assert actions == 2


@pytest.mark.parametrize(
    "action, job_name, out_kind, wrong_kind",
    [
        # Wrong kind: ask fmu_export to run a ModelCheck job
        ("fmu_export", "ModelCheckJob", "fmu_ME", "ME"),
        ("fmu_export", "CodeGenerationJob", "fmu_CS", "CE"),
    ],
    ids=["fmu_export_wrong_jog_kind", "fmu_export_wrong_fmu_kind"],
)
@pytest.mark.skipif(not is_windows, reason="FMU export is only supported on Windows.")
def test_scadeone_actions_fmu_export_wrong_kind(
    action, job_name, out_kind, wrong_kind, tmp_path
):
    """
    Test fmu_export with a job of the wrong kind (e.g., ModelCheckJob).
    Outputs are directed under tmp_path to avoid repo writes.
    """
    if out_kind == "fmu_ME":
        out = tmp_path / "unit_tests_out_fail" / "exported_model_ME"
        extra = ["-o", str(out)]
        extra += ["-k", wrong_kind]  # FMU export flag
    elif out_kind == "fmu_CS":
        out = tmp_path / "unit_tests_out_fail" / "exported_model_CS"
        extra = ["-o", str(out)]
        extra += ["-k", wrong_kind]  # FMU export flag
    else:
        raise RuntimeError("Unsupported out_kind in parametrization")
    actions = scadeone_actions.scadeone_actions(
        [
            action,
            "-s",
            scade_home_dir,
            "-p",
            str(sproj),
            "-j",
            job_name,
            *extra,
        ]
    )
    assert actions == 2
