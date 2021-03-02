#!/usr/bin/env python3
import pytest


def test_bake_project(cookies):
    result = cookies.bake(template=str(pytest.cookie_template))
    assert result.exit_code == 0
    assert result.exception is None
    assert result.project.basename == "slurm"
    assert result.project.isdir()


def read_settings(text):
    d = {}
    for line in text.split("\n"):
        line_bare = line.strip()
        bits = line_bare.split()
        if not bits:
            continue
        d[bits[0]] = line_bare
    return d


def test_cluster_name(cookies):
    result = cookies.bake(template=str(pytest.cookie_template))
    settings_dict = read_settings(result.project.join("cookiecutter_settings.py").read())
    sbatch_defaults = settings_dict["SBATCH_DEFAULTS"]
    assert '""""""' in sbatch_defaults
    cluster = settings_dict["CLUSTER_NAME"]
    assert cluster == 'CLUSTER_NAME = """"""'

    result = cookies.bake(
        template=str(pytest.cookie_template), extra_context={"cluster_name": "dusk"}
    )
    settings_dict = read_settings(result.project.join("cookiecutter_settings.py").read())
    cluster = settings_dict["CLUSTER_NAME"]
    assert cluster == 'CLUSTER_NAME = """dusk"""'
