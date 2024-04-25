![Test
SnakemakeProfiles/slurm](https://github.com/Snakemake-Profiles/slurm/workflows/Test%20SnakemakeProfiles/slurm/badge.svg)

# Contents

- [Introduction](#introduction)
- [Alternatives](#alternatives)
- [Quickstart](#quickstart)
- [Examples](#examples)
    - [Example 1: project setup to use specific slurm
      account](#example-1-project-setup-to-use-specific-slurm-account)
    - [Example 2: project setup using a specified
      cluster](#example-2-project-setup-using-a-specified-cluster)
- [Profile details](#profile-details)
    - [Cookiecutter options](#cookiecutter-options)
    - [Default snakemake arguments](#default-snakemake-arguments)
    - [Parsing arguments to SLURM (sbatch) and resource
      configuration](#parsing-arguments-to-slurm-sbatch-and-resource-configuration)
    - [Rule specific resource
      configuration](#rule-specific-resource-configuration)
    - [Cluster configuration file](#cluster-configuration-file)
- [Tests](#tests)
    - [Testing on a HPC running
      SLURM](#testing-on-a-hpc-running-slurm)
    - [Testing on machine without
      SLURM](#testing-on-machine-without-slurm)
    - [Baking cookies](#baking-cookies)
    - [Anatomy of the tests (WIP)](#anatomy-of-the-tests-wip)
    - [Adding new tests (WIP)](#adding-new-tests-wip)

> [!IMPORTANT]
>
> **Snakemake version 8 unsupported**
>
> Snakemake version 8 introduces breaking changes with respect to the Snakemake cookiecutter profile. One new
> feature is that execution of jobs on a cluster or the cloud are handled by
> [executor plugins](https://snakemake.readthedocs.io/en/stable/tutorial/additional_features.html#cluster-or-cloud-execution).
> For instance, there is a
> [dedicated executor plugin for SLURM](https://snakemake.github.io/snakemake-plugin-catalog/plugins/executor/slurm.html) that
> provides much of the functionality that was previously catered for by this snakemake profile. Profiles are still needed, but their
> role changes somewhat to that of fine-tuning executor plugins for particular sites, only requiring the yaml configuration
> file.
>
> With this in mind, support for Snakemake version 8 has currently been put on hold and I recommend that users consult
> the executor plugin documentation for slurm.
>

## Introduction

This cookiecutter provides a template Snakemake profile for configuring
Snakemake to run on the [SLURM Workload
Manager](https://slurm.schedmd.com/) for **Snakemake version <=7**. The profile defines the following scripts

1. `slurm-submit.py` - submits a jobscript to slurm
2. `slurm-jobscript.sh` - a template jobscript
3. `slurm-status.py` - checks the status of jobs in slurm
4. `slurm-sidecar.py` - run a Snakemake cluster sidecar for caching queries to Slurm's controller/database daemons

and a configuration file `config.yaml` that defines default values for
snakemake command line arguments.

Given an installed profile `profile_name`, when snakemake is run with
`--profile profile_name`, the configuration keys and values from
`config.yaml` are passed to snakemake - plus any additional options to
snakemake that the user has applied.

Note that the use of option `--cluster-config` is discouraged, but the
profile still provides support for backwards compatibility. The default
configuration file therefore contains a commented section with examples
of resource configuration (see also [snakemake best
practices](https://snakemake.readthedocs.io/en/stable/snakefiles/best_practices.html?highlight=set-resources#best-practices)):

    # Example resource configuration
    # default-resources:
    #   - runtime=100
    #   - mem_mb=6000
    #   - disk_mb=1000000
    # # set-threads: map rule names to threads
    # set-threads:
    #   - single_core_rule=1
    #   - multi_core_rule=10
    # # set-resources: map rule names to resources in general
    # set-resources:
    #   - high_memory_rule:mem_mb=12000
    #   - long_running_rule:runtime=1200

See the [snakemake documentation on
profiles](https://snakemake.readthedocs.io/en/stable/executing/cli.html?highlight=profile#profiles)
for more information.

## Alternatives

For a more light-weight alternative, see the excellent repo
[smk-simple-slurm](https://github.com/jdblischak/smk-simple-slurm) by
@jdblischak. In particular, it can handle larger amounts of jobs than
this profile (see [issue
#79](https://github.com/Snakemake-Profiles/slurm/issues/79)).

## Quickstart

To create a slurm profile from the
[cookiecutter](https://github.com/cookiecutter/cookiecutter), simply run

    # create config directory that snakemake searches for profiles (or use something else)
    profile_dir="${HOME}/.config/snakemake"
    mkdir -p "$profile_dir"
    # use cookiecutter to create the profile in the config directory
    template="gh:Snakemake-Profiles/slurm"
    cookiecutter --output-dir "$profile_dir" "$template"

You will be prompted to set some values for your profile (here assumed
to be called `profile_name`), after which the profile scripts and
configuration file will be installed in `$profile_dir` as
`profile_name/`. Then you can run Snakemake with

    snakemake --profile profile_name ...

Note that the `--profile` argument can be either a relative or absolute
path. In addition, snakemake will search for a corresponding folder
`profile_name` in `/etc/xdg/snakemake` and `$HOME/.config/snakemake`,
where globally accessible profiles can be placed.

## Examples

### Example 1: project setup to use specific slurm account

One typical use case is to setup a profile to use a specific slurm
account:

    $ cookiecutter --output-dir "$profile_dir" "$template"
    profile_name [slurm]: slurm.my_account
    sbatch_defaults []: account=my_account no-requeue exclusive
    cluster_sidecar_help: [Use cluster sidecar. NB! Requires snakemake >= 7.0! Enter to continue...]
    Select cluster_sidecar:
    1 - yes
    2 - no
    Choose from 1, 2 [1]:
    cluster_name []:
    cluster_config_help: [The use of cluster-config is discouraged. Rather, set snakemake CLI options in the profile configuration file (see snakemake documentation on best practices). Enter to continue...]
    cluster_config []:

The command `snakemake --profile slurm.my_account ...` will submit jobs
with `sbatch --parsable --account=my_account --no-requeue --exclusive`.
Note that the option `--parsable` is always added.

### Example 2: project setup using a specified cluster

It is possible to install multiple profiles in a project directory.
Assuming our HPC defines a [multi-cluster
environment](https://slurm.schedmd.com/multi_cluster.html), we can
create a profile that uses a specified cluster:

    $ cookiecutter slurm
    profile_name [slurm]: slurm.dusk
    sbatch_defaults []: account=my_account
	cluster_sidecar_help: [Use cluster sidecar. NB! Requires snakemake >= 7.0! Enter to continue...]
    Select cluster_sidecar:
    1 - yes
    2 - no
    Choose from 1, 2 [1]:
    cluster_name []: dusk
    cluster_config_help: [The use of cluster-config is discouraged. Rather, set snakemake CLI options in the profile configuration file (see snakemake documentation on best practices). Enter to continue...]
    cluster_config []:

(Note that once a cookiecutter has been installed, we can reuse it
without using the github URL).

The command `snakemake --profile slurm.dusk ...` will now submit jobs
with `sbatch --parsable --account=my_account --cluster=dusk`. In
addition, the `slurm-status.py` script will check for jobs in the `dusk`
cluster job queue.

## Profile details

### Cookiecutter options

- `profile_name` : A name to address the profile via the `--profile`
  Snakemake option.
- `use_singularity`: This sets the default `--use-singularity`
  parameter. Default is not to use (`false`).
- `use_conda`: This sets the default `--use-conda` parameter. Default
  is not to use (`false`).
- `jobs`: This sets the default `--cores`/`--jobs`/`-j` parameter.
- `restart_times`: This sets the default `--restart-times`/`-T`
  parameter.
- `max_status_checks_per_second`: This sets the default
  `--max-status-checks-per-second` parameter.
- `max_jobs_per_second`: This sets the default `--max-jobs-per-second`
  parameter.
- `latency_wait`: This sets the default
  `--latency-wait`/`--output-wait`/`-w` parameter.
- `print_shell_commands`: This sets the default
  `--printshellcmds`/`-p` parameter.
- `sbatch_defaults` : List of (space-separated) default arguments to
  sbatch, e.g.: `qos=short time=60`. Note, we support [human-friendly
  time specification](#human-friendly-time).
- `cluster_sidecar`: Whether to use the [cluster sidecar](https://snakemake.readthedocs.io/en/stable/tutorial/additional_features.html?highlight=sidecar#using-cluster-sidecar) feature. (Requires Snakemake version of at least 7.0)
- `cluster_name` : some HPCs define multiple SLURM clusters. Set the
  cluster name, leave empty to use the default. This will add the
  `--cluster` string to the sbatch defaults, and adjust
  `slurm-status.py` to check status on the relevant cluster.
- `cluster_jobname`: A pattern to use for naming Slurm
  jobs ([`--job-name`](https://slurm.schedmd.com/sbatch.html#OPT_job-name)).
  See [Patterns](#patterns) below. Set to `"""` (i.e., blank) to use the slurm default.
- `cluster_logpath`: A pattern to use for setting
  the [`--output`](https://slurm.schedmd.com/sbatch.html#OPT_output)
  and [`--error`](https://slurm.schedmd.com/sbatch.html#OPT_error) log files. You can
  use [slurm filename patterns](https://slurm.schedmd.com/sbatch.html#lbAH)
  and [Patterns](#patterns). Set to `"""` (i.e., blank) to use the slurm default. For
  example, `logs/slurm/%r_%w` creates logs named `%r_%w.out` and `%r_%w.err` in the
  directory `logs/slurm`.
- `cluster_config` (NB: discouraged): Path to a YAML or JSON
  configuration file analogues to the Snakemake [`--cluster-config`
  option](https://snakemake.readthedocs.io/en/stable/snakefiles/configuration.html#cluster-configuration-deprecated)
  .
  Path may be relative to the profile directory or absolute including
  environment variables (e.g.
  `$PROJECT_ROOT/config/slurm_defaults.yaml`).

#### Patterns

For job name and log paths we provide a custom pattern syntax. 

- `%r`: Rule name. If it is a group job, the group ID will be used instead.
- `%i`: Snakemake job ID.
- `%w`: Wildcards string. e.g., wildcards A and B will be concatenated as `A=<val>.B=<val>`
- `%U`: A [random universally unique identifier](https://docs.python.org/3/library/uuid.html#uuid.uuid4) (UUID).
- `%S`: A shortened version of `%U`. For example, `16fd2706-8baf-433b-82eb-8c7fada847da` would become `16fd2706`.
- `%T`: The [Unix timestamp](https://docs.python.org/3/library/time.html#time.time) (rounded to an integer).

### Default snakemake arguments

Other default arguments to `snakemake` may be adjusted in the resulting
`<profile_name>/config.yaml` file.

### Parsing arguments to SLURM (sbatch) and resource configuration

NB!!! As previusly pointed out, the use of cluster-config is
discouraged. Rule specific resource configuration is better handled by
snakemake's CLI arguments (see [snakemake best
practices](https://snakemake.readthedocs.io/en/stable/snakefiles/best_practices.html?highlight=set-resources#best-practices))
which can be put in the profile configuration file.

Arguments are set and overridden in the following order and must be
named according to [sbatch long option
names](https://slurm.schedmd.com/sbatch.html):

1) `sbatch_defaults` cookiecutter option
2) Profile `cluster_config` file `__default__` entries
3) Snakefile threads and resources (time, mem)
4) Profile `cluster_config` file `<rulename>`{=html} entries
5) `--cluster-config` parsed to Snakemake (deprecated since Snakemake
   5.10)
6) Snakemake CLI resource configuration in profile configuration file

### Rule specific resource configuration

In addition to Snakemake CLI resource configuration, resources can be
specified in Snakefile rules and must all be in the correct unit/format
as expected by `sbatch` ([except time](#human-friendly-time)). The
implemented resource names are given (and may be adjusted) in
`slurm-submit.py`'s variable `RESOURCE_MAPPING`. This is intended for
system agnostic resources such as time and memory. Currently supported
resources are `time`, `mem`, `mem-per-cpu`, `nodes`, and `partition`. An
example rule resources configuration follows:

    rule bwa_mem:
        resources:
            time = "00:10:00",
            mem = 12000,
            partition = "debug"

Resources not listed in `RESOURCE_MAPPING` can also be specified with
the special `slurm` parameter to resources. For example, to specify
a specific QoS and 2 GPU resources for a rule `gpu_stuff`

    rule gpu_stuff:
        resources:
            time="12:00:00",
            mem_mb=8000,
            partition="gpu",
            slurm="qos=gpuqos gres=gpu:2"

Note: `slurm` **must** be a space-separated string of the form `<option>=<value>`. The `<option>` names must match the 
**long** option name of sbatch (see list
[here](https://slurm.schedmd.com/sbatch.html#SECTION_OPTIONS); can be
snake_case or kebab-case). Flags (i.e., options that do not take a
value) should be given without a value. For example, to use the
wait flag, you would pass `slurm="qos=gpuqos wait"`.

#### Human-friendly time

We support specifying the time for a rule in a "human-friendly" format.
For example, a rule with a time limit of 4 hours and 30 minutes can be
specified as `time="4h30m"`.

Supported (case-insensitive) time units are:

- `w`: week
- `d`: day
- `h`: hour
- `m`: minute
- `s`: second

However, you may also pass the time in the [slurm
format](https://slurm.schedmd.com/sbatch.html#OPT_time).

### Cluster configuration file

Although [cluster configuration has been officially
deprecated](https://snakemake.readthedocs.io/en/stable/snakefiles/configuration.html#cluster-configuration-deprecated)
in favor of profiles since snakemake 5.10, the `--cluster-config` option
can still be used to configure default and per-rule options. Upon
creating a slurm profile, the user will be prompted for the location of
a cluster configuration file, which is a YAML or JSON file (see example
below).

``` yaml
__default__:
  account: staff
  mail-user: slurm@johndoe.com

large_memory_requirement_job:
  constraint: mem2000MB
  ntasks: 16
```

The `__default__` entry will apply to all jobs.

## Tests

Tests can be run on a HPC running SLURM or locally in a docker stack. To
execute tests, run

    pytest -v -s tests

from the source code root directory. Test options can be configured via
the pytest configuration file `tests/pytest.ini`.

Test dependencies are listed in `test-environment.yml` and can be
installed in e.g. a conda environment.

### Testing on a HPC running SLURM

Test fixtures are setup in [temporary directories created by
pytest](https://docs.pytest.org/en/stable/tmpdir.html). Usually fixtures
end up in /tmp/pytest-of-user or something similar. In any case, these
directories are usually not accessible on the nodes where the tests are
run. Therefore, when running tests on a HPC running SLURM, by default
tests fixtures will be written to the directory `.pytest` relative to
the current working directory (which should be the source code root!).
You can change the location with the `pytest` option `--basetemp`.

### Testing on machine without SLURM

For local testing the test suite will deploy a docker stack
`cookiecutter-slurm` that runs two services based on the following
images:

1. [quay.io/biocontainers/snakemake](https://quay.io/repository/biocontainers/snakemake?tab=tags)
2. [giovtorres/docker-centos7-slurm](https://github.com/giovtorres/docker-centos7-slurm)

The docker stack will be automatically deployed provided that the user
has installed docker and enabled [docker
swarm](https://docs.docker.com/engine/swarm/) (`docker swarm init`). The
docker stack can also be deployed manually from the top-level directory
as follows:

    DOCKER_COMPOSE=tests/docker-compose.yaml ./tests/deploystack.sh

See the deployment script `tests/deploystack.sh` for details.

### Baking cookies

Testing of the cookiecutter template is enabled through the [pytest
plugin for Cookiecutters](https://github.com/hackebrot/pytest-cookies).

### Anatomy of the tests (WIP)

The slurm tests all depend on fixtures and fixture factories defined in
`tests/conftest.py` to function properly. The `cookie_factory` fixture
factory generates slurm profiles, and the `data` fixture copies the
files `tests/Snakefile` and `tests/cluster-config.yaml` to the test
directory. There is also a `datafile` fixture factory that copies any
user-provided data file to the test directory. Finally, the `smk_runner`
fixture provides an instance of the `tests/wrapper.SnakemakeRunner`
class for running Snakemake tests.

As an example, `tests/test_slurm_advanced.py` defines a fixture
`profile` that uses the `cookie_factory` fixture factory to create an
slurm profile that uses advanced argument conversion:

    @pytest.fixture
    def profile(cookie_factory, data):
        cookie_factory(advanced="yes")

The test `tests/test_slurm_advanced.py::test_adjust_runtime` depends on
this fixture and `smk_runner`:

    def test_adjust_runtime(smk_runner, profile):
        smk_runner.make_target(
            "timeout.txt", options=f"--cluster-config {smk_runner.cluster_config}"
        )

The `make_target` method makes a snakemake target with additional
options passed to Snakemake.

### Adding new tests (WIP)

See `tests/test_issues.py` and `tests/Snakefile_issue49` for an example
of how to write a test with a custom Snakefile.
