# -*- coding: future_fstrings -*-
import requests
import tempfile
import re
import os
import subprocess
import packaging.version
import pkg_resources
from pathlib import Path
from .util import (
    combine_volumes,
    find_storage_path_from_other_machine,
    dict_to_toml,
    clone_repo,
    re_github,
)
import tomlkit


class DockFill_Python:
    def __init__(self, anysnake):
        self.anysnake = anysnake
        self.python_version = self.anysnake.python_version

        self.paths = self.anysnake.paths

        self.paths.update(
            {
                "storage_python": find_storage_path_from_other_machine(
                    self.anysnake, Path("python") / self.python_version
                ),
                "docker_storage_python": "/anysnake/python",
                # "docker_code": "/project/code",
                "log_python": self.paths["log_storage"]
                / f"anysnake.python.{self.python_version}.log",
            }
        )
        self.volumes = {
            anysnake.paths["docker_storage_python"]: anysnake.paths["storage_python"]
        }

    def get_additional_docker_build_cmds(self):
        if self.python_version.startswith("2"):
            # python beyond these versions needs libssl 1.1
            # the older ones need libssl1.0
            # on older debians/ubuntus that would be libssl-dev
            # but on 18.04+ it's libssl1.0-dev
            # and we're not anticipating building on something older
            return "\nRUN apt-get install -y libssl1.0-dev\n"
        else:
            return ""

    def pprint(self):
        print(f"  Python version={self.python_version}")

    def ensure(self):

        python_version = self.anysnake.python_version

        return self.anysnake.build(
            target_dir=self.paths["storage_python"],
            target_dir_inside_docker=self.paths["docker_storage_python"],
            relative_check_filename="bin/virtualenv",
            log_name="log_python",
            additional_volumes={},
            version_check=self.check_python_version_exists,
            root=True,
            build_cmds=f"""
#/bin/bash
cd ~/
git clone http://github.com/pyenv/pyenv.git
cd pyenv/plugins/python-build
./install.sh

export MAKE_OPTS=-j{self.anysnake.cores}
export CONFIGURE_OPTS=--enable-shared
export PYTHON_CONFIGURE_OPTS=--enable-shared
python-build {python_version} {self.paths['docker_storage_python']}
#curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
#{self.paths['docker_storage_python']}/bin/python get-pip.py
{self.paths['docker_storage_python']}/bin/pip install -U pip virtualenv
chown {os.getuid()}:{os.getgid()} {self.paths['docker_storage_python']} -R
echo "done"
""",
        )

    def check_python_version_exists(self):
        version = self.python_version
        r = requests.get("https://www.python.org/doc/versions/").text
        if not (
            f'release/{version}/"' in r or f'release/{version}"'
        ):  # some have / some don't
            raise ValueError(
                f"Unknown python version {version} - check https://www.python.org/doc/versions/"
            )

    def freeze(self):
        return {"base": {"python": self.python_version}}


def safe_name(name):
    return pkg_resources.safe_name(name).lower()


class _Dockfill_Venv_Base:
    def create_venv(self):
        additional_cmd = ""
        if self.python_version[0] == "2":
            additional_cmd = f"{self.target_path_inside_docker}/bin/pip install pyopenssl ndg-httpsclient pyasn1"
        return self.anysnake.build(
            target_dir=self.target_path,
            target_dir_inside_docker=self.target_path_inside_docker,
            relative_check_filename=Path("bin") / "activate.fish",
            log_name=f"log_{self.name}_venv",
            additional_volumes=self.dockfill_python.volumes,
            build_cmds=f"""
{self.paths['docker_storage_python']}/bin/virtualenv -p {self.paths['docker_storage_python']}/bin/python {self.target_path_inside_docker}
{additional_cmd}
echo "done"
""",
        )


class Dockfill_PythonPoetry(_Dockfill_Venv_Base):
    def __init__(self, anysnake, dockfill_python):
        self.anysnake = anysnake
        self.paths = self.anysnake.paths
        self.python_version = self.anysnake.python_version
        self.dockfill_python = dockfill_python
        self.name = "python_poetry"
        self.paths.update(
            {
                "poetry_venv": (
                    self.paths["storage"] / "poetry_venv" / self.python_version
                ),
                "docker_poetry_venv": "/anysnake/poetry_venv",
                "log_python_poetry_venv": self.paths["log_storage"]
                / f"anysnake.poetry_venv.{self.python_version}.log",
            }
        )
        self.target_path = self.paths["poetry_venv"]
        self.target_path_inside_docker = self.paths["docker_poetry_venv"]
        self.volumes = {}

    def pprint(self):
        pass

    def ensure(self):
        res = self.create_venv()
        res |= self.install_poetry()
        return res

    def install_poetry(self):
        poetry_bin = Path(self.target_path / "bin" / "poetry")
        if not poetry_bin.exists():
            print("install poetry")
            volumes_ro = self.dockfill_python.volumes.copy()
            volumes_rw = {self.target_path_inside_docker: self.target_path}
            env = {}
            paths = [self.target_path_inside_docker + "/bin"]

            env["EXTPATH"] = ":".join(paths)
            cmd = "/anysnake/poetry_venv/bin/pip install poetry"
            if self.python_version[0] == "2":
                cmd += f" pyopenssl ndg-httpsclient pyasn1"
            return_code, logs = self.anysnake._run_docker(
                f"""
    #!/bin/bash
        export PATH=$PATH:$EXTPATH
    {cmd}
        echo "done"
    
        """,
                {
                    "volumes": combine_volumes(ro=volumes_ro, rw=volumes_rw),
                    "environment": env,
                },
                f"log_python_poetry_venv",
                append_to_log=True,
            )
            return True  # please run post_build_cmd
        return False


class _DockerFillVenv(_Dockfill_Venv_Base):
    def __init__(self):
        self.paths.update(
            {
                f"log_{self.name}_venv": (
                    self.log_path / f"anysnake.{self.name}_venv.log"
                ),
                f"log_{self.name}_venv_poetry": (
                    self.log_path / f"anysnake.{self.name}_venv_poetry.log"
                ),
                f"log_{self.name}_venv_poetry_cmd": (
                    self.log_path / f"anysnake.{self.name}_venv_poetry_cmd.log"
                ),
            }
        )
        self.poetry_path = self.clone_path / f"poetry_{self.anysnake.python_version}"
        self.poetry_path.mkdir(exist_ok=True, parents=True)
        self.poetry_path_inside_docker = str(
            Path(self.clone_path_inside_docker) / f"poetry_{self.anysnake.python_version}"
        )

    def ensure(self):
        res = self.create_venv()
        res |= self.fill_venv()
        return res

    def fill_venv(self, rebuild=False):
        code_packages = {
            k: v
            for (k, v) in self.packages.items()
            if v.startswith("@git+")
            or v.startswith("@hg+")
            or v.startswith("@")
            and re.match(re_github, v[1:])  # github
        }
        code_names = set(code_packages.keys())
        any_cloned = self.clone_code_packages(code_packages)
        if rebuild or any_cloned:
            # force rebuild
            if Path(self.poetry_path / "pyproject.toml").exists():
                Path(self.poetry_path / "pyproject.toml").unlink()
        packages_missing = set([safe_name(x) for x in self.packages]) - set(
            [
                safe_name(x)
                for x in self.find_installed_packages(
                    self.anysnake.major_python_version
                )
            ]
        )

        return self.install_with_poetry(self.packages, code_packages, packages_missing)

    def clone_code_packages(self, code_packages):
        result = set()
        for name, url_spec in code_packages.items():
            log_key = f"log_{self.name}_venv_{name}"
            self.paths[log_key + "_clone"] = self.log_path / (
                f"anysnake.{self.name}_venv_{name}.pip.log"
            )
            target_path = self.clone_path / name
            with open(str(self.paths[log_key + "_clone"]), "wb") as log_file:
                if not target_path.exists():
                    result.add(name)
                    url = url_spec
                    clone_repo(url, name, target_path, log_file)

        return result

    def find_installed_packages(self, major_python_version):
        return list(self.find_installed_package_versions(major_python_version).keys())

    def find_extras(self, editable_package):
        import configparser

        fn = self.clone_path / editable_package / "setup.cfg"
        if fn.exists():
            c = configparser.ConfigParser()
            c.read(str(fn))
            try:
                return list(set(c["options.extras_require"].keys()) - set(["doc"]))
            except KeyError:
                pass
        return []

    def find_installed_package_versions(self, major_python_version):
        venv_dir = (
            self.target_path
            / "lib"
            / ("python" + major_python_version)
            / "site-packages"
        )
        result = {}
        for p in venv_dir.glob("*"):
            if p.name.endswith(".dist-info"):
                name = p.name[: p.name.rfind("-", 0, -5)]
                version = p.name[p.name.rfind("-", 0, -5) + 1 : -1 * len(".dist-info")]
                result[safe_name(name)] = version
            elif p.name.endswith(".egg-link"):
                name = p.name[: -1 * len(".egg-link")]
                version = "unknown"
                result[safe_name(name)] = version
            elif p.name.endswith(".so"):
                name = p.name[: p.name.find(".")]
                version = "unknown"
                result[safe_name(name)] = version

        return result

    def install_with_poetry(self, packages, editable_packages, packages_missing):
        """packages are parse_requirements results with method == 'pip'
        we now use poetry for this
        
        """
        toml = f"""
[tool.poetry]
    name = "{self.anysnake.project_name}"
    version = "0.1.0"
    description = ""
    authors = []

[build-system"]
    requires =  ["poetry>=0.12"]
    build-backend = "poetry.masonry.api"

[tool.poetry.dependencies]
    python = "{self.anysnake.python_version}"
"""
        for k, v in sorted(packages.items()):
            if k not in editable_packages and safe_name(k) not in editable_packages:
                toml += f'\t{k} = "{v}"\n'
            else:
                extras = [f'"{x}"' for x in self.find_extras(k)]
                toml += f'\t{k} = {{path = "{self.clone_path_inside_docker}/{k}", extras = [{", ".join(extras)}], develop = true}}\n'
        new_toml = toml
        pyproject_toml = Path(self.poetry_path / "pyproject.toml")
        pyproject_toml.parent.mkdir(exist_ok=True)
        if pyproject_toml.exists():
            old_toml = pyproject_toml.read_text()
        else:
            old_toml = ""
        if new_toml != old_toml or packages_missing:
            print(f"poetry for {self.name} (slow, stand by)")
            import difflib
            for row in (difflib.context_diff(old_toml.split("\n") ,new_toml.split("\n"))):
                print(row)
            pyproject_toml.write_text(new_toml)
            cmd = [
                f"source {self.target_path_inside_docker}/bin/activate",
                f"cd {self.poetry_path_inside_docker} && {self.paths['docker_poetry_venv']}/bin/poetry update --verbose",
            ]
            cmd = "\n".join(cmd)
            # poetry cache needs to be writable, and we're not mounting .cache
            # by default in .ensure dockers.
            pypoetry_cache_path = Path("~").expanduser() / ".cache" / "pypoetry"
            pypoetry_cache_path.mkdir(parents=True, exist_ok=True)
            volumes_ro = self.dockfill_python.volumes.copy()
            volumes_rw = {
                self.target_path_inside_docker: self.target_path,
                self.clone_path_inside_docker: self.clone_path,
                self.paths["docker_poetry_venv"]: self.paths["poetry_venv"],
                pypoetry_cache_path: pypoetry_cache_path
            }
            env = {}
            paths = [self.target_path_inside_docker + "/bin"]
            if self.anysnake.dockfill_rust is not None:  # if we have a rust, use it
                volumes_ro.update(self.anysnake.dockfill_rust.volumes)
                volumes_rw.update(self.anysnake.dockfill_rust.rw_volumes)
                paths.append(self.anysnake.dockfill_rust.shell_path)
                env.update(self.anysnake.dockfill_rust.env)
            from .cli import home_files

            home_inside_docker = self.anysnake.paths['home_inside_docker']
            for h in home_files:
                p = Path("~").expanduser() / h
                if p.exists():
                    volumes_ro[str(Path(home_inside_docker) / h)] = p
            env["EXTPATH"] = ":".join(paths)
            # /anysnake/code_venv/bin /anysnake/cargo/bin /anysnake/code_venv/bin /anysnake/storage_venv/bin /anysnake/R/bin /usr/local/sbin /usr/local/bin /usr/sbin /usr/bin /sbin /bin /machine/opt/infrastructure/client /machine/opt/infrastructure/repos/FloatingFileSystemClient
            return_code, logs = self.anysnake._run_docker(
                f"""
    #!/bin/bash
        export PATH=$PATH:$EXTPATH
        echo "Path: $PATH"
    {cmd}
        echo "done"
    
        """,
                {
                    "volumes": combine_volumes(ro=volumes_ro, rw=volumes_rw),
                    "environment": env,
                },
                f"log_{self.name}_venv_poetry",
            )
            installed_now = self.find_installed_packages(
                self.anysnake.major_python_version
            )
            still_missing = set([safe_name(k) for k in packages.keys()]).difference(
                [safe_name(k) for k in installed_now]
            )
            if still_missing:
                msg = f"Installation of packages failed: {still_missing}\n"
            elif (isinstance(return_code, int) and (return_code != 0)) or (
                not isinstance(return_code, int) and (return_code["StatusCode"] != 0)
            ):
                msg = f"Installation of packages failed: return code was not 0 (was {return_code})\n"
            else:
                msg = ""
            if msg:
                print(self.paths[f"log_{self.name}_venv_poetry"].read_text())
                raise ValueError(
                    msg
                    + "Check log in "
                    + str(self.paths[f"log_{self.name}_venv_poetry"])
                )
            return True
        else:
            return False  # everything ok


class DockFill_GlobalVenv(_DockerFillVenv):
    def __init__(self, anysnake, dockfill_python):
        self.anysnake = anysnake
        self.paths = self.anysnake.paths
        self.python_version = self.anysnake.python_version
        self.name = "storage"
        self.paths.update(
            {
                "storage_venv": (self.paths["storage"] / "venv" / self.python_version),
                "docker_storage_venv": "/anysnake/storage_venv",
                "storage_clones": self.paths["storage"] / "code",
                "docker_storage_clones": "/anysnake/storage_venv_clones",
            }
        )
        self.target_path = self.paths["storage_venv"]
        self.target_path_inside_docker = self.paths["docker_storage_venv"]
        self.clone_path = self.paths["storage_clones"]
        self.clone_path_inside_docker = self.paths["docker_storage_clones"]
        self.log_path = self.paths["log_storage"]

        self.dockfill_python = dockfill_python
        self.volumes = {
            anysnake.paths["docker_storage_venv"]: self.paths["storage_venv"],
            anysnake.paths["docker_storage_clones"]: self.paths["storage_clones"],
        }
        self.packages = self.anysnake.global_python_packages
        self.shell_path = str(Path(self.paths["docker_storage_venv"]) / "bin")
        super().__init__()

    def pprint(self):
        print("  Global python packages")
        for entry in self.anysnake.global_python_packages.items():
            print(f"    {entry}")

    def freeze(self):
        """Return a toml string with all the installed versions"""
        result = {}
        for k, v in self.find_installed_package_versions(
            self.anysnake.major_python_version
        ).items():
            result[k] = f"{v}"
        return {"global_python": result}


class DockFill_CodeVenv(_DockerFillVenv):
    def __init__(self, anysnake, dockfill_python, dockfill_global_venv):
        self.anysnake = anysnake
        self.dockfill_global_venv = dockfill_global_venv
        self.paths = self.anysnake.paths
        self.name = "code"
        self.log_path = self.paths["log_code"]
        self.python_version = self.anysnake.python_version
        self.paths.update(
            {
                "code_venv": self.paths["code"] / "venv" / self.python_version,
                "docker_code_venv": "/anysnake/code_venv",
                "code_clones": self.paths["code"],
                "docker_code_clones": self.paths["docker_code"],
            }
        )
        self.target_path = self.paths["code_venv"]
        self.target_path_inside_docker = self.paths["docker_code_venv"]
        self.clone_path = self.paths["code_clones"]
        self.clone_path_inside_docker = self.paths["docker_code_clones"]
        self.dockfill_python = dockfill_python
        self.volumes = {anysnake.paths[f"docker_code_venv"]: self.paths["code_venv"]}
        self.rw_volumes = {anysnake.paths[f"docker_code"]: self.paths["code"]}
        self.packages = self.anysnake.local_python_packages
        self.shell_path = str(Path(self.paths["docker_code_venv"]) / "bin")
        super().__init__()

    def ensure(self):
        super().ensure()
        self.copy_bins_from_global()
        self.fill_sitecustomize()
        return False

    def copy_bins_from_global(self):
        source_dir = self.paths["storage_venv"] / "bin"
        target_dir = self.paths["code_venv"] / "bin"
        for input_fn in source_dir.glob("*"):
            if not input_fn.is_dir() and not input_fn.is_symlink():
                output_fn = target_dir / input_fn.name
                if not output_fn.exists():
                    input = input_fn.read_bytes()
                    if input.startswith(b"#"):
                        n_pos = input.find(b"\n")
                        first_line = input[:n_pos]
                        if (
                            first_line
                            == f"#!{self.paths['docker_storage_venv']}/bin/python".encode(
                                "utf-8"
                            )
                        ):
                            output = (
                                f"#!{self.paths['docker_code_venv']}/bin/python".encode(
                                    "utf-8"
                                )
                                + input[n_pos:]
                            )
                            output_fn.write_bytes(output)
                    else:
                        output_fn.write_bytes(input)
                    output_fn.chmod(input_fn.stat().st_mode)
        pth_path = (
            self.paths["code_venv"]
            / "lib"
            / ("python" + self.anysnake.major_python_version)
            / "site-packages"
            / "anysnake.pth"
        )
        if not pth_path.exists():
            pth_path.write_text(
                str(
                    self.paths["docker_storage_venv"]
                    / "lib"
                    / ("python" + self.anysnake.major_python_version)
                    / "site-packages"
                )
                + "\n"
            )

    def pprint(self):
        print("  Local python packages")
        for entry in self.anysnake.local_python_packages.items():
            print(f"    {entry}")

    def fill_sitecustomize(self):
        lib_code = (
            Path(self.paths["docker_code_venv"])
            / "lib"
            / ("python" + self.anysnake.major_python_version)
        )
        lib_storage = (
            Path(self.paths["docker_storage_venv"])
            / "lib"
            / ("python" + self.anysnake.major_python_version)
        )
        if "docker_storage_rpy2" in self.paths:
            lib_rpy2 = (
                Path(self.paths["docker_storage_rpy2"])
                / "lib"
                / ("python" + self.anysnake.major_python_version)
            )
            rpy2_venv_str = f"'{lib_rpy2}/site-packages',"
        else:
            rpy2_venv_str = ""
        sc_file = str(
            self.paths["code_venv"]
            / "lib"
            / ("python" + self.anysnake.major_python_version)
            / "site-packages"
            / "sitecustomize.py"
        )

        tf = open(sc_file, "w")
        tf.write(
            f"""
import sys
for x in [
    {rpy2_venv_str}
    '{lib_storage}/site-packages',
    '{lib_code}/site-packages',
    '{lib_code}',
    ]:
    if x in sys.path:
        sys.path.remove(x)
    sys.path.insert(0, x)
"""
        )
        tf.flush()

    def rebuild(self):
        self.fill_venv(rebuild=True)

    def fill_venv(self, rebuild=False):
        super().fill_venv(rebuild=rebuild)
        return False

    def freeze(self):
        """Return a toml string with all the installed versions"""
        result = {}
        for k, v in self.find_installed_package_versions(
            self.anysnake.major_python_version
        ).items():
            result[k] = f"{v}"
        return {"python": result}
