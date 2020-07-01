# -*- coding: future_fstrings -*-
import os
import tempfile
import click
import click_completion

click_completion.init()

from pathlib import Path
from mbf_anysnake import parse_requirements, parsed_to_anysnake
import subprocess
from .util import get_next_free_port


config_file = "anysnake.toml"
home_files = [".hgrc", ".git-credentials", ".gitconfig"]
home_dirs = [
    ".config/fish",
    ".config/matplotlib",
    ".cache/matplotlib",
    ".jupyter",
    ".local/share/fish",
    ".local/share/jupyter",
    ".ipython",
]


@click.group()
def main():
    pass


def get_anysnake():
    parsed = parse_requirements(config_file)
    return parsed_to_anysnake(parsed), parsed


def get_volumes_config(config, key2):
    """Extract a volumes config from the config if present.

    Representation is a dictionary, 
        target_path:  source_path
    """
    result = {}
    for key1 in ["global_run", "run"]:
        if key1 in config and key2 in config[key1]:
            for (f, t) in config[key1][key2]:  # from / to
                result[t] = Path(f).expanduser().absolute()
    return result


@main.command()
@click.option("--do-time", default=False, is_flag=True)
def build(do_time=False):
    """Build everything if necessary - from docker to local venv from project.setup 
    Outputs full docker_image:tag
    """
    d, _ = get_anysnake()
    d.ensure(do_time)
    print(d.docker_image)
    return d


@main.command()
def rebuild():
    """for each locally cloned package in code,
    call python setup.py install
    """
    d, config = get_anysnake()
    d.rebuild()


@main.command()
@click.argument("packages", nargs=-1, required=True)
def remove_pip(packages):
    """Remove pip modules, from anysnake.toml. 
    If they're installed, remove their installation
    If they're editable, remove their code/folders as well"""
    import shutil
    import tomlkit

    d, config = get_anysnake()
    local_config = tomlkit.loads(Path("anysnake.toml").read_text())
    write_toml = False
    for p in packages:
        if p in local_config.get("python"):
            del local_config["python"][p]
            write_toml = True
        path = d.paths["code_clones"] / p
        if path.exists():
            if click.confirm(f"really remove {path}?)"):
                shutil.rmtree(str(path))
        lib_path = (
            d.paths["code_venv"]
            / "lib"
            / ("python" + d.major_python_version)
            / "site-packages"
        )
        print(p + "*")
        for f in lib_path.glob(p + "*"):
            print(f)

    if write_toml:
        import time

        backup_filename = "anysnake.toml.%s" % time.strftime("%Y-%M-%d-%H-%M")
        print("writing new anysnake.toml - old one in %s" % backup_filename)
        shutil.copy("anysnake.toml", backup_filename)
        with open("anysnake.toml", "w") as op:
            op.write(tomlkit.dumps(local_config))


@main.command()
def rebuild_global_venv():
    raise ValueError("todo")


@main.command()
@click.option(
    "--no-build/--build",
    default=False,
    help="don't perform build if things are missing",
)
@click.option(
    "--allow-writes/--no-allow-writes", default=False, help="mount all volumes rw"
)
@click.option(
    "--include-perf/--no-include-perf",
    default=False,
    help="include perf tool for profiling",
)
def shell(no_build=False, allow_writes=False, include_perf=False):
    """Run a shell with everything mapped (build if necessary)"""

    d, config = get_anysnake()
    if not no_build:
        d.ensure()
    else:
        d.ensure_just_docker()
    cmd = "/usr/bin/fish"
    if include_perf:
        cmd = (
            "sudo apt-get update;\nsudo apt-get install -y linux-tools-common linux-tools-generic linux-tools-`uname -r`\n"
            + cmd
        )
    d.mode = 'shell'
    print(
        d.run(
            cmd,
            allow_writes=allow_writes,
            home_files=home_files,
            home_dirs=home_dirs,
            volumes_ro=get_volumes_config(config, "additional_volumes_ro"),
            volumes_rw=get_volumes_config(config, "additional_volumes_rw"),
        )
    )


@main.command()
@click.option("--no-build/--build", default=False)
@click.option("--pre/--no-pre", default=True, help="run pre_run_inside/outside")
@click.option("--post/--no-post", default=True, help="run post_run_inside/outside")
@click.argument("cmd", nargs=-1)
def run(cmd, no_build=False, pre=True, post=True):
    """Run a command"""
    import subprocess

    d, config = get_anysnake()
    if not no_build:
        d.ensure()
    else:
        d.ensure_just_docker()

    pre_run_outside = config.get("run", {}).get("pre_run_outside", False)
    pre_run_inside = config.get("run", {}).get("pre_run_inside", False)
    if pre and pre_run_outside:
        subprocess.Popen(pre_run_outside, shell=True).communicate()
    cmd = "\n" + " ".join(cmd) + "\n"
    if pre and pre_run_inside:
        cmd = pre_run_inside + cmd
    post_run_outside = config.get("run", {}).get("post_run_outside", False)
    post_run_inside = config.get("run", {}).get("post_run_inside", False)
    if post and post_run_inside:
        cmd += post_run_inside
    d.mode = 'run'
    print(
        d.run(
            cmd,
            allow_writes=False,
            home_files=home_files,
            home_dirs=home_dirs,
            volumes_ro=get_volumes_config(config, "additional_volumes_ro"),
            volumes_rw=get_volumes_config(config, "additional_volumes_rw"),
        )
    )
    if post and post_run_outside:
        subprocess.Popen(post_run_outside, shell=True).communicate()


def check_if_nb_extensions_are_activated():
    """Check if the nb extensions are activated"""
    try:
        d = Path("~/.jupyter/jupyter_notebook_config.json").expanduser().read_text()
        return '"jupyter_nbextensions_configurator": true' in d
    except IOError:
        return False


@main.command()
@click.option("--no-build/--build", default=False)
def jupyter(no_build=False):
    """Run a jupyter with everything mapped (build if necessary)"""

    d, config = get_anysnake()
    if not no_build:
        d.ensure()
    else:
        d.ensure_just_docker()
    host_port = get_next_free_port(8888)
    print("Starting notebook at %i" % host_port)
    nbextensions_not_activated = not check_if_nb_extensions_are_activated()
    if not 'jupyter_contrib_nbextensions' in d.global_python_packages:
        d.global_python_packages['jupyter_contrib_nbextensions'] = ''

    jupyter_r_kernel = ""
    if d.R_version >= "3.6":
        # this is shit.
        # it will enable this by writing to home/.local/share/jupyter
        # which will be shared by all anysnake runs
        # independent of actual R version (and we need R 3.6 / bioconductor 3.10
        # to actually have an R-kernel available.
        # oh well, it's still much easier and less insane than the other variants
        # of having a dockfill if jupyter get's installed and R > ...
        if not Path("~/.local/share/jupyter/kernels/ir").expanduser().exists():
            jupyter_r_kernel = "echo 'IRkernel::installspec()' | R --no-save --quiet\n"

    d.mode = 'jupyter'
    d.run(
        (
        """
        jupyter contrib nbextension install --user --symlink
        jupyter nbextensions_configurator enable --user
        """
            if nbextensions_not_activated
            else ""
        )
        + jupyter_r_kernel
        + config.get('jupyter', {}).get('pre_run_inside','')
        + """jupyter notebook --ip=0.0.0.0 --no-browser\n"""
        + config.get('jupyter', {}).get('post_run_inside',''),
        home_files=home_files,
        home_dirs=home_dirs,
        volumes_ro=get_volumes_config(config, "additional_volumes_ro"),
        volumes_rw=get_volumes_config(config, "additional_volumes_rw"),
        ports=[(host_port, 8888)],
    )


@main.command()
@click.option("--no-build/--build", default=False)
@click.argument('regexps', nargs=-1)
def instant_browser(regexps, no_build=False):
    """Run an instant_browser with everything mapped (build if necessary).


    """
    host_port = get_next_free_port(8888)
    print("Starting instant_browser at %i" % host_port)
    d, config = get_anysnake()
    if not no_build:
        d.ensure()
    else:
        d.ensure_just_docker()

    d.mode = 'instant_browser'
    d.run(
        "instant_browser " + " ".join(regexps,),
        home_files=home_files,
        home_dirs=home_dirs,
        volumes_ro=get_volumes_config(config, "additional_volumes_ro"),
        volumes_rw=get_volumes_config(config, "additional_volumes_rw"),
        ports=[(host_port, 8888)],
    )



@main.command()
def docker_tag():
    """return the currently used docker_tag 
    for integration purposes"""
    d, config = get_anysnake()
    print(d.docker_image)


@main.command()
@click.option("--no-build/--build", default=False)
def ssh(no_build=False):
    """Run an sshd with everything mapped (build if necessary),
    using your authorized_keys keys from ~/.ssh

    You might want to use additional_volumes_ro to map in
    some host keys (
        "/etc/ssh/ssh_host_ecdsa_key",
        "/etc/ssh/ssh_host_ed25519_key",
        "/etc/ssh/ssh_host_rsa_key",
    ).
    
    """

    d, config = get_anysnake()
    if not no_build:
        d.ensure()
    else:
        d.ensure_just_docker()
    host_port = get_next_free_port(8822)
    print("Starting sshd at %i" % host_port)
    if not ".vscode-remote" in home_dirs:
        home_dirs.append(".vscode-remote")
    home_files.append(".ssh/authorized_keys")

    tf = tempfile.NamedTemporaryFile(mode="w", suffix=".env")
    tf.write(
        "\n".join(
            [
                f"{key}={value}"
                for (key, value) in d.get_environment_variables({}).items()
            ]
        )
    )
    tf.flush()

    volumes_ro = get_volumes_config(config, "additional_volumes_ro")
    volumes_ro[Path(tf.name)] = Path(d.paths['home_inside_docker']) / ".ssh/environment"
    import pprint

    pprint.pprint(volumes_ro)
    d.run(
        f"""
        echo "now starting ssh server"
        echo "Port 8822\nPermitUserEnvironment yes\n" >/tmp/sshd_config
        sudo /usr/sbin/sshd -D -f /tmp/sshd_config
        #/usr/bin/fish
        """,
        home_files=home_files,
        home_dirs=home_dirs,
        volumes_ro=volumes_ro,
        volumes_rw=get_volumes_config(config, "additional_volumes_rw"),
        ports=[(host_port, 8822)],
    )


@main.command()
@click.argument("modules", nargs=-1)
@click.option("--report-only/--no-report-only", default=False)
def test(modules, report_only):
    """Run pytest on all (or a subset) modules that were in the code path and had a tests/conftest.py"""
    from . import testing

    d, config = get_anysnake()
    d.ensure()
    testing.run_tests(modules, d, config, report_only)


@main.command()
def show_config():
    """Print the config as it is actually used"""
    d, parsed = get_anysnake()
    d.pprint()
    print("")
    print("Additional volumes")
    print("  RO")
    for outside, inside in get_volumes_config(parsed, "additional_volumes_ro").items():
        print(f"    {outside} -> {inside}")
    print("  RW")
    for outside, inside in get_volumes_config(parsed, "additional_volumes_rw").items():
        print(f"    {outside} -> {inside}")
    print("")
    print("Config files used:", parsed["used_files"])


@main.command()
def show_paths():
    """Print the config as it is actually used"""
    d, parsed = get_anysnake()
    import pprint

    print("paths detected")
    pprint.pprint(d.paths)


@main.command()
def default_config():
    """Print a default config"""
    p = Path("anysnake.toml")
    print(
        """[base]
# docker image to use/build
# use image:tag for full spec
# or just 'image' for auto_build from mbf_anysnake
# docker specs
docker_image="mbf_anysnake_18.04"

# optional global config to import
# global_config="/etc/anysnake.tompl"

# python version to use
python="3.7.2"

# project_name = folder name of anysnake.toml by default, overwrite here
# project_name="example"

# bioconductor version to use, R version and CRAN dates are derived from this
# (optional) 
bioconductor="3.8"

# cran options are 'minimal' (just what's needed from bioconductor) and 'full'
# (everything)
cran="full"

# rpy2 version to use.
# rpy2_version = "3.2.0"


# where to store the installations
# python, R, global virtual enviromnments, bioconductor, cran
storage_path="/var/lib/anysnake"

# local venv, editable libraries
code_path="code"

# install all bioconductor packages whether they need experimental or annotation
# data or not.
# bioconductor_whitelist=["_full_"]
# or install selected packages otherwise omited like this
# bioconductor_whitelist=["chimera"]

# include rust (if you use bioconductor, rust 1.30.0 will be added automatically)
# rust = ["1.30.0", "nigthly-2019-03-20"]

[run]
# additional folders to map into docker
additional_volumes_ro = [['/opt', '/opt']]
additional_volumes_rw = [['/home/some_user/.hgrc', '/home/u1000/.hgrc']]
pre_run_outside = \"""
        echo "bash script, runs outside of the continer before 'run'"
\"""

pre_run_inside = \"""
        echo "bash script, runs inside of the continer before 'run' (ie. after pre_run_outside)"
\"""
post_run_inside = "echo 'bash script running inside container after run cmd'"
post_run_outside = "echo 'bash script running outside container after run cmd'"

# python packages installed into global storage
[global_python]
jupyter=""

# python packages installed locally
[python]
pandas=">=0.23"
# an editable library
dppd="@git+https://github.com/TyberiusPrime/dppd"
# github integration
dppd_plotine="@gh/TyberiusPrime/dppd"

# additional @something urls for [python]
# [pip_regexps]
# @mbf/something ->
# "@mbf/(.+)"="@hg+https://mysite.com/hg/\\1"
# or just @mbf with 'smart' substitiution.
# @mbf"=["@hg+https://mysite.com/hg/\\1"@

# environmental variables inside the container
[env]
INSIDE_ANYSNAKE="yes"


"""
    )


def merge_dicts(a, b, path=None):
    "merges b into a"
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge_dicts(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                raise Exception("Conflict at %s" % ".".join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


@main.command()
def freeze():
    """Output installed packages in anysnake.toml format"""
    import tomlkit

    d, parsed = get_anysnake()
    output = {}
    for s in d.strategies:
        if hasattr(s, "freeze"):
            merge_dicts(output, s.freeze())
    print(tomlkit.dumps(output))


@main.command()
def version():
    import mbf_anysnake

    print("mbf_anysnake version %s" % mbf_anysnake.__version__)


@main.command()
@click.option(
    "-i", "--case-insensitive/--no-case-insensitive", help="Case insensitive completion"
)
@click.argument(
    "shell",
    required=False,
    type=click_completion.DocumentedChoice(click_completion.core.shells),
)
def show_completion(shell, case_insensitive):
    """Show the click-completion-command completion code
    ie. what you need to add to your shell configuration.
    """
    extra_env = (
        {"_CLICK_COMPLETION_COMMAND_CASE_INSENSITIVE_COMPLETE": "ON"}
        if case_insensitive
        else {}
    )
    click.echo(click_completion.core.get_code(shell, extra_env=extra_env))

@main.command()
def enter():
    """exec a fish shell in anysnake docker running from this folder. 
    Will prompt if there are multiple available
    """
    import json
    import sys
    cwd = str(Path('.').absolute())
    d, parsed = get_anysnake()
    lines = subprocess.check_output(['docker','ps']).decode('utf-8').split("\n")
    candidates = []
    for l in lines:
        if d.docker_image in l:
            docker_id = l[:l.find(" ")]
            info = json.loads(subprocess.check_output(['docker','inspect', docker_id]).decode('utf-8'))[0]
            env = info.get('Config', {}).get('Env', {})
            found = False
            mode = '??'
            for e in env:
                e = e.split("=", 1)
                if e[0] =="ANYSNAKE_PROJECT_PATH" and e[1] == cwd: 
                    found = True
                elif e[0] =="ANYSNAKE_MODE":
                    mode = e[1]
            if found:
                #if mode in ('run','??', 'jupyter'):
                candidates.append((docker_id,info.get('Name', '?'), mode))
    if len(candidates) == 0:
        print("No docker to enter found")
        sys.exit(0)
    elif len(candidates) == 1:
        print("Entering only available docker")
        pass
    else:
        print("Pick one")
        for (ii, (docker_id, name, mode)) in enumerate(candidates):
            print(ii, name, mode)
        chosen = sys.stdin.readline().strip()
        chosen = int(chosen)
        candidates = [candidates[ii]]
    if candidates:
        print("Entering ", candidates[0][1])
        cmd = ['docker', 'exec', '-it', candidates[0][0], 'fish']
        p = subprocess.Popen(cmd)
        p.communicate()
        sys.exit(0)
            
    #print(d.docker_image)

if __name__ == "__main__":
    main()
