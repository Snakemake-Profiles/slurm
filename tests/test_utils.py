#!/usr/bin/env python3
import os
import re
import sys
import subprocess
import pytest
from docker.models.containers import Container

sys.path.append(
    os.path.join(os.path.dirname(__file__), os.pardir, "{{cookiecutter.profile_name}}")
)
import slurm_utils  # noqa: E402


@pytest.fixture
def mock_get_cluster_config(smk_runner, monkeypatch):
    if isinstance(smk_runner._container, Container):
        class MockPopen:
            def __init__(self, cmd, **kwargs):
                self._res = smk_runner.exec_run(cmd)

            def communicate(self):
                return (self._res.output, None)

        monkeypatch.setattr(subprocess, "Popen", MockPopen)


@pytest.fixture
def mock_get_default_partition(smk_runner, monkeypatch):
    if isinstance(smk_runner._container, Container):
        def mock_res(cmd, **kwargs):
            res = smk_runner.exec_run(cmd)
            return res.output

        monkeypatch.setattr(subprocess, "check_output", mock_res)


def test_time_to_minutes():
    minutes = slurm_utils.time_to_minutes("foo")
    assert minutes is None
    minutes = slurm_utils.time_to_minutes("10-00:00:10")
    assert minutes == 14401
    minutes = slurm_utils.time_to_minutes("10:00:00")
    assert minutes == 600
    minutes = slurm_utils.time_to_minutes("100:00")
    assert minutes == 100
    minutes = slurm_utils.time_to_minutes("20")
    assert minutes == 20


def test_cluster_configuration(request, mock_get_cluster_config):
    partition = request.config.getoption("--partition")
    df = slurm_utils._get_cluster_configuration(partition)
    assert re.match(r"^\d+$", str(df["TIMELIMIT_MINUTES"][0]))


def test_argument_conversion(request, mock_get_cluster_config,
                             mock_get_default_partition):
    partition = request.config.getoption("--partition")
    config = slurm_utils._get_cluster_configuration(partition)
    args = {"mem": min(config["MEMORY"]) / min(config["CPUS"]) * 2}
    d = slurm_utils.advanced_argument_conversion(args)
    assert d["cpus-per-task"] == 2
    max_cpus = max(config["CPUS"])
    args = {"cpus-per-task": max_cpus * 2}
    d = slurm_utils.advanced_argument_conversion(args)
    assert d["cpus-per-task"] == max_cpus


@pytest.mark.docker
def test_default_partition(mock_get_default_partition):
    p = slurm_utils._get_default_partition()
    assert p == "normal"
