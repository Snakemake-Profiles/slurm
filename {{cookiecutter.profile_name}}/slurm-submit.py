#!/usr/bin/env python3
"""
Snakemake SLURM submit script.
"""
import json
import logging
import os

import requests
from snakemake.utils import read_job_properties

import slurm_utils
from CookieCutter import CookieCutter

logger = logging.getLogger(__name__)

SIDECAR_VARS = os.environ.get("SNAKEMAKE_CLUSTER_SIDECAR_VARS", None)
DEBUG = bool(int(os.environ.get("SNAKEMAKE_SLURM_DEBUG", "0")))

if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.DEBUG)


def register_with_sidecar(jobid):
    if SIDECAR_VARS is None:
        return
    sidecar_vars = json.loads(SIDECAR_VARS)
    url = "http://localhost:%d/job/register/%s" % (sidecar_vars["server_port"], jobid)
    logger.debug("POST to %s", url)
    headers = {"Authorization": "Bearer %s" % sidecar_vars["server_secret"]}
    requests.post(url, headers=headers)


# cookiecutter arguments
SBATCH_DEFAULTS = CookieCutter.SBATCH_DEFAULTS
CLUSTER = CookieCutter.get_cluster_option()
CLUSTER_CONFIG = CookieCutter.CLUSTER_CONFIG

RESOURCE_MAPPING = {
    "time": ("time", "runtime", "walltime"),
    "mem": ("mem", "mem_mb", "ram", "memory"),
    "mem-per-cpu": ("mem-per-cpu", "mem_per_cpu", "mem_per_thread"),
    "nodes": ("nodes", "nnodes"),
    "partition": ("partition", "queue"),
}

# parse job
jobscript, dependencies = slurm_utils.parse_jobscript()
job_properties = read_job_properties(jobscript)

sbatch_options = {}
cluster_config = slurm_utils.load_cluster_config(CLUSTER_CONFIG)

# 1) sbatch default arguments and cluster
sbatch_options.update(slurm_utils.parse_sbatch_defaults(SBATCH_DEFAULTS))
sbatch_options.update(slurm_utils.parse_sbatch_defaults(CLUSTER))

# 2) cluster_config defaults
sbatch_options.update(cluster_config["__default__"])

# 3) Convert resources (no unit conversion!) and threads
sbatch_options.update(slurm_utils.convert_job_properties(job_properties, RESOURCE_MAPPING))

# 4) cluster_config for particular rule
sbatch_options.update(cluster_config.get(job_properties.get("rule"), {}))

# 5) cluster_config options
sbatch_options.update(job_properties.get("cluster", {}))

# convert human-friendly time - leaves slurm format time as is
if "time" in sbatch_options:
    duration = str(sbatch_options["time"])
    sbatch_options["time"] = str(slurm_utils.Time(duration))

# 6) Add job dependencies for immediate-submit
if dependencies:
    sbatch_options.update({'dependency': ':'.join(['afterok'] + dependencies)})

# 7) Format pattern in snakemake style
sbatch_options = slurm_utils.format_values(sbatch_options, job_properties)

# 8) create output and error filenames and paths
joblog = slurm_utils.JobLog(job_properties)
log = ""
if "output" not in sbatch_options and CookieCutter.get_cluster_logpath():
    outlog = joblog.outlog
    log = outlog
    sbatch_options["output"] = outlog

if "error" not in sbatch_options and CookieCutter.get_cluster_logpath():
    errlog = joblog.errlog
    log = errlog
    sbatch_options["error"] = errlog

# ensure sbatch output dirs exist
for o in ("output", "error"):
    slurm_utils.ensure_dirs_exist(sbatch_options[o]) if o in sbatch_options else None

# 9) Set slurm job name
if "job-name" not in sbatch_options and "job_name" not in sbatch_options:
    sbatch_options["job-name"] = joblog.jobname

# submit job and echo id back to Snakemake (must be the only stdout)
jobid = slurm_utils.submit_job(jobscript, **sbatch_options)
logger.debug("Registering %s with sidecar...", jobid)
register_with_sidecar(jobid)
logger.debug("... done registering with sidecar")
print(jobid)
