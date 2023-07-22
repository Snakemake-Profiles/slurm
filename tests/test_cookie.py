#!/usr/bin/env python3
import sys
import pytest
from unittest.mock import patch


@pytest.mark.parametrize("sidecar", ["yes", "no"])
def test_bake_project(cookies, sidecar):
    result = cookies.bake(template=str(pytest.cookie_template),
                          extra_context={"cluster_sidecar": sidecar})
    cfg = result.project_path / "config.yaml"
    if sidecar == "yes":
        assert "cluster-sidecar: \"slurm-sidecar.py\"\n" in cfg.read_text()
    else:
        assert "cluster-sidecar: \"slurm-sidecar.py\"" not in cfg.read_text()
    assert result.exit_code == 0
    assert result.exception is None
    assert result.project_path.name == "slurm"
    assert result.project_path.is_dir()


def test_cookiecutter(cookies, monkeypatch):
    result = cookies.bake(template=str(pytest.cookie_template))
    assert result.exit_code == 0
    assert result.exception is None

    assert result.project_path.name == "slurm"
    assert result.project_path.is_dir()
    with patch.dict(sys.modules):
        if "CookieCutter" in sys.modules:
            del sys.modules["CookieCutter"]
        monkeypatch.syspath_prepend(str(result.project_path))
        from CookieCutter import CookieCutter
        assert CookieCutter.SBATCH_DEFAULTS == ""
        assert CookieCutter.CLUSTER_NAME == ""
        assert CookieCutter.CLUSTER_CONFIG == ""
        assert CookieCutter.get_cluster_option() == ""


def test_cookiecutter_extra_context(cookies, monkeypatch):
    result = cookies.bake(template=str(pytest.cookie_template),
                          extra_context={"sbatch_defaults": "account=foo",
                                         "cluster_name": "dusk",
                                         "cluster_config": "slurm.yaml"})
    assert result.exit_code == 0
    assert result.exception is None

    assert result.project_path.name == "slurm"
    assert result.project_path.is_dir()
    with patch.dict(sys.modules):
        if "CookieCutter" in sys.modules:
            del sys.modules["CookieCutter"]
        monkeypatch.syspath_prepend(str(result.project_path))
        from CookieCutter import CookieCutter
        assert CookieCutter.SBATCH_DEFAULTS == "account=foo"
        assert CookieCutter.CLUSTER_NAME == "dusk"
        assert CookieCutter.CLUSTER_CONFIG == "slurm.yaml"
        assert CookieCutter.get_cluster_option() == "--cluster=dusk"
