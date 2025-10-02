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

import inspect
import shutil
import sys
from argparse import ArgumentParser
from pathlib import Path

from ansys.scadeone.core.job import Job, JobType
from ansys.scadeone.core.scadeone import ScadeOne

from utilities import get_scade_one_home, sone2junit

# -*- coding: utf-8 -*-

"""
Scade One Python actions
========================================

This module provides actions to interact with Scade One tools to be run in an automated environment like a CI/CD pipeline.
prerequisites:
- uses the Scade One install path defined in S_ONE_HOME environment variable if set
  or uses the Scade One installation directories passed as an argument
  if S_ONE_HOME or the parameter are not set, it will try to find Scade One installation directories in the Windows registry and use the most recent one
- The Scade One Python API (pyscadeone) must be installed and available in the Python environment
"""

__author__ = "Ansys, Inc."
__version__ = "0.1.0"
__license__ = "MIT"
__status__ = "Development"
__all__ = ["ScadeOneActions"]


class ScadeOneActions:
    """
    The ScadeOneActions class provides actions to interact with Scade One tools
    It checks if Scade One is installed and provides methods to run available Scade One tools & services (pre/post processing)
    """

    s_one_api = None

    def __init__(self, scade_one_home=None):
        self.set_scade_one_home(scade_one_home, strict=False)

    def set_scade_one_home(self, scade_one_home=None, strict=True):
        """Set or update the Scade One API."""
        if scade_one_home is None:
            # Get the Scade One home directory from environment variable or registry
            scade_one_home = get_scade_one_home()

        if scade_one_home is None:
            if strict:
                raise FileNotFoundError(
                    "Scade One home directory not found. Set S_ONE_HOME environment variable or pass the path as an argument."
                )
        else:
            # Check if the Scade One home directory exists
            s_one_install = Path(scade_one_home)
            if not s_one_install.is_dir() and strict:
                raise FileNotFoundError(
                    f"No Scade One installation directory found in:{scade_one_home}"
                )
            else:
                print(f"Scade One home directory set to: {s_one_install}")
                # initialize the Scade One Python API
                self.s_one_api = ScadeOne(install_dir=s_one_install)

    def register_actions(
        self, subparsers: ArgumentParser, global_parser: ArgumentParser = None
    ):
        # Automatically find methods starting with 'action_'
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if name.startswith("action_"):
                action_name = name[7:]  # Remove 'action_' prefix
                help_text = method.__doc__ or ""
                parser = subparsers.add_parser(
                    action_name, help=help_text, parents=[global_parser]
                )
                # Look for a corresponding _args_<action_name> method to add arguments
                args_method = getattr(self, f"_args_{action_name}", None)
                if args_method:
                    args_method(parser)
                parser.set_defaults(func=method)

    def _job_args(self, parser):
        """Add common job arguments for Scade One actions"""
        parser.add_argument(
            "-p",
            "--project",
            required="True",
            help="Scade One Project file (.sproj)",
            type=Path,
        )
        parser.add_argument(
            "-j",
            "--job",
            required="True",
            help="Name of the job to generate code for",
            type=str,
        )
        parser.add_argument(
            "-o",
            "--output",
            help="output path to save job output",
            type=Path,
            default=None,
        )

    def _get_job_type(self, args, jobtype) -> tuple[Job, str]:
        """Get a job from a Scade One project with the specified job type"""
        if args.project.is_file():
            # Load the Scade One project
            project = self.s_one_api.load_project(args.project)
            # get the job in the project
            project.load_jobs()
            job = project.get_job(args.job)

            if not job:
                return (
                    None,
                    f"Error: Job '{args.job}' not found in project {args.project}",
                )

            # Check if the job is of the right type
            if job._kind != jobtype:
                return (
                    None,
                    f"Error: Job '{args.job}' is not a {jobtype} job in project {args.project}",
                )
            else:
                return job, f"Job '{args.job}' found in project {args.project}"
        else:
            return None, f"Error: Scade One project {args.project} doesn't exist"

    def _args_model_check(self, parser):
        """Add arguments for the model_check action"""
        self._job_args(parser)

    def action_model_check(self, args):
        """Check the model in a Scade One project for errors and warnings"""
        job, message = self._get_job_type(args, JobType.MODEL_CHECK)
        if not job:
            return 2, message
        # Execute the job
        result = job.run()
        message = result.message

        if result.code == 0 and args.output:
            # Save check report in a folder specified by args.output
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(job.storage.path.parent / "out" / "log.txt", args.output)
            message += "\n" + f"Model check report saved to {args.output}"

        return result.code, message

    def _args_code_gen(self, parser):
        """Only common job arguments for the code-gen action"""
        self._job_args(parser)

    def action_code_gen(self, args):
        """Generate C code from a job in a Scade One project"""
        job, message = self._get_job_type(args, JobType.CODE_GENERATION)
        if not job:
            return 2, message
        # Execute the job
        result = job.run()
        message = result.message

        if result.code == 0 and args.output:
            # Save generated code in a folder specified by args.output
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(
                job.storage.path.parent / "out", args.output, dirs_exist_ok=True
            )
            message += "\n" + f"Generated code saved to {args.output} folder"

        return result.code, message

    def _args_tests_exec(self, parser):
        """Only common job arguments for the test_exec action"""
        self._job_args(parser)
        parser.add_argument(
            "--junit",
            help="Junit file path to save the tests report",
            type=Path,
            default=None,
        )

    def action_tests_exec(self, args):
        """Execute tests cases from a job in a Scade One project"""
        job, message = self._get_job_type(args, JobType.TEST_EXECUTION)
        if not job:
            return 2, message
        # Execute the job
        result = job.run()
        message = result.message

        if result.code == 0 and args.junit:
            # Save JUnit XML results in a file specified by args.junit
            sone_test_file = job.storage.path.parent / "out" / job.test_result_file
            junit_message = sone2junit(sone_test_file, Path(args.junit))
            message += "\n" + junit_message
        return result.code, message


def scadeone_actions(args=None):
    """Scade One Python actions"""
    # Create a parser for global options only
    global_parser = ArgumentParser(add_help=False)
    # Add --scade_one_home as a global argument
    global_parser.add_argument(
        "-s",
        "--scade_one_home",
        help="Scade One home installation path",
        type=str,
        default=None,
    )

    # Create the main parser, inheriting global options
    parser = ArgumentParser(
        description="Scade One Python actions", parents=[global_parser]
    )

    subparsers = parser.add_subparsers(
        title="Commands",
        help="Use: command --help for help (ex: python scadeone_actions.py check --help)",
        dest="action",
        required=True,
    )

    # Create an instance of ScadeOneActions to register actions
    # This will also initialize the Scade One API with the default or provided path as environment variable
    s_one_actions = ScadeOneActions(scade_one_home=None)
    s_one_actions.register_actions(subparsers, global_parser=global_parser)

    # Parse all arguments
    parsed_args = parser.parse_args(args)

    # If scade_one_home is provided, re-initialize with the correct path
    if parsed_args.scade_one_home:
        s_one_actions.set_scade_one_home(parsed_args.scade_one_home)

    if parsed_args.action:
        code, message = parsed_args.func(parsed_args)
        print(message)
        return code

    return 1


if __name__ == "__main__":
    sys.exit(scadeone_actions())
