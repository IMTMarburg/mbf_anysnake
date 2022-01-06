# -*- coding: future_fstrings -*-
from pathlib import Path
from docker import from_env as docker_from_env
import time
import pwd
import tempfile
import shutil
import subprocess
import os
import multiprocessing
import sys
import json

import mbf_anysnake
from .dockfill_docker import DockFill_Docker
from .dockfill_python import (
    DockFill_Python,
    DockFill_GlobalVenv,
    DockFill_CodeVenv,
    Dockfill_PythonPoetry,
)
from .dockfill_clone import DockFill_Clone
from .dockfill_r import DockFill_R, DockFill_Rpy2
from .dockfill_bioconductor import DockFill_Bioconductor
from .dockfill_rust import DockFill_Rust
from .util import combine_volumes, get_next_free_port


class Anysnake:
    """Wrap ubuntu version (=docker image),
    Python version,
    R version,
    bioconductor version,
    global and local venvs (including 'code')

    bioconductor_version can be set to None, then no bioconductor is installed,
    R_version can be set to None, then no (if bioconductor == None) or the
        matching R version for the bioconductor is being installed.
    If bioconductor_version is set, R_version must not be set.

    """

    def __init__(
        self,
        project_name,
        docker_image,
        python_version,
        bioconductor_version,
        r_version,
        rpy2_version,
        global_python_packages,
        local_python_packages,
        bioconductor_whitelist,
        cran_mode,
        storage_path,
        storage_per_hostname,
        code_path,
        code_path_docker,
        cores=None,
        cran_mirror="https://cloud.r-project.org",
        environment_variables={},
        post_build_cmd=False,
        rust_versions=[],
        cargo_install=[],
        ports=[],
        docker_build_cmds="",
        global_clones={},
        local_clones={},
        per_user = None
    ):
        self.cores = cores if cores else multiprocessing.cpu_count()
        self.cran_mirror = cran_mirror
        if not self.cran_mirror.endswith("/"):
            self.cran_mirror += "/"

        self.storage_path = Path(storage_path)
        self.storage_per_hostname = storage_per_hostname

        docker_tag = docker_image[docker_image.rfind(":") + 1 :]
        if docker_tag == '%md5sum%':
            storage_path = (
                storage_path / docker_image[: docker_image.rfind(":")]
            ).absolute()
        else:
            storage_path = (storage_path / docker_image.replace(":", "__")).absolute()
        code_path = Path(code_path).absolute()
        self.storage_per_hostname = bool(storage_per_hostname)

        if per_user is None:
            per_user = Path("~").expanduser() / ".anysnake"
        else:
            per_user = per_user / self.get_login_username()

        bin_path = Path(mbf_anysnake.__path__[0]).parent.parent / "bin"
        self.paths = {
            "bin": bin_path,
            "storage": storage_path,
            "code": code_path,
            "docker_code": code_path_docker,
            "log_storage": storage_path / "logs",
            "log_code": code_path / "logs",
            "per_user": per_user,
            "home_inside_docker": "/home/%s" % self.get_login_username(),
        }
        self.paths["per_user"].mkdir(exist_ok=True, parents=True)

        dfd = DockFill_Docker(self, docker_build_cmds)
        self.project_name = project_name

        self.python_version = python_version
        self.bioconductor_version = bioconductor_version
        self.global_python_packages = global_python_packages
        self.local_python_packages = local_python_packages
        self.bioconductor_whitelist = bioconductor_whitelist
        self.rpy2_version = rpy2_version
        self.cran_mode = cran_mode
        self.post_build_cmd = post_build_cmd
        self.rust_versions = rust_versions
        self.cargo_install = cargo_install
        self.ports = ports
        self.docker_build_cmds = docker_build_cmds
        self.global_clones = global_clones
        self.local_clones = local_clones
        dfp = DockFill_Python(self)
        dfgv = DockFill_GlobalVenv(self, dfp)
        if self.rust_versions:
            self.dockfill_rust = DockFill_Rust(
                self, self.rust_versions, self.cargo_install
            )
        else:
            self.dockfill_rust = None
        self.strategies = [
            x
            for x in [
                dfd,
                self.dockfill_rust,
                dfp,
                Dockfill_PythonPoetry(self, dfp),
                DockFill_CodeVenv(
                    self, dfp, dfgv
                ),  # since I want them earlier in the path!
                dfgv,
            ]
            if x is not None
        ]
        dfr = None
        if r_version:
            self.R_version = r_version
            dfr = DockFill_R(self)
        else:
            if self.bioconductor_version:
                self.R_version = DockFill_Bioconductor.find_r_from_bioconductor(self)
                dfr = DockFill_R(self)
            else:
                self.R_version = None
        if self.R_version is not None and self.R_version < "3.0":
            raise ValueError("Requested an R version that is not rpy2 compatible")

        if dfr:
            self.strategies.append(dfr)
            self.strategies.append(DockFill_Rpy2(self, dfp, dfr))
            if self.bioconductor_version:
                self.strategies.append(DockFill_Bioconductor(self, dfr))

        self.strategies.append(DockFill_Clone(self))
        for k, v in self.paths.items():
            self.paths[k] = Path(v)
        self.environment_variables = dict(environment_variables)
        for df in self.strategies:
            if hasattr(df, "env"):
                self.environment_variables.update(df.env)

        if docker_image.endswith(":%md5sum%"):
            docker_image = docker_image[: docker_image.rfind(":")]
            docker_image += ":" + dfd.get_dockerfile_hash(docker_image)
        self.docker_image = str(docker_image)
        self.mode = "unknown"

    def pprint(self):
        print("Anysnake")
        print(f"  Storage path: {self.paths['storage']}")
        print(f"  local code path: {self.paths['code']}")
        print(f"  global logs in: {self.paths['log_storage']}")
        print(f"  local logs in: {self.paths['log_code']}")
        print("")
        for s in self.strategies:
            s.pprint()

        # Todo: cran
        # todo: modularize into dockerfills

    def ensure(self, do_time=False):
        self.paths["storage"].mkdir(parents=True, exist_ok=True)
        self.paths["code"].mkdir(parents=False, exist_ok=True)

        self.paths["log_storage"].mkdir(parents=False, exist_ok=True)
        self.paths["log_code"].mkdir(parents=False, exist_ok=True)

        run_post_build = False
        for s in self.strategies:
            start = time.time()
            run_post_build |= s.ensure()
            if do_time:
                print(s.__class__.__name__, time.time() - start)
        if run_post_build and self.post_build_cmd:
            import subprocess

            print("running", self.post_build_cmd)
            p = subprocess.Popen(
                str(self.post_build_cmd), cwd=str(self.paths["storage"]), shell=True
            )
            p.communicate()

    def ensure_just_docker(self):
        for s in self.strategies:
            if isinstance(s, DockFill_Docker):
                s.ensure()

    def rebuild(self):
        for s in self.strategies:
            if hasattr(s, "rebuild"):
                s.rebuild()

    def get_environment_variables(self, env_base, ports):
        env = env_base.copy()
        env = env.copy()
        for k in self.environment_variables.keys():
            # don't use update here - won't work with the toml object
            env[k] = self.environment_variables[k]
        env["ANYSNAKE_PROJECT_PATH"] = Path(".").absolute()
        env["ANYSNAKE_USER"] = self.get_login_username()
        env["ANYSNAKE_MODE"] = self.mode
        env["ANYSNAKE_PORTS"] = json.dumps(ports)
        return env

    def _build_cmd(
        self,
        bash_script,
        env={},
        ports={},
        py_spy_support=True,
        home_files={},
        home_dirs={},
        volumes_ro={},
        volumes_rw={},
        allow_writes=False,
    ):
        """
        ports is merged with those defined in the config/object creation
        """
        env = self.get_environment_variables(env, ports)

        # docker-py has no concept of interactive dockers
        # dockerpty does not work with current docker-py
        # so we use the command line interface...

        tf = tempfile.NamedTemporaryFile(mode="w")
        path_str = (
            ":".join(
                [x.shell_path for x in self.strategies if hasattr(x, "shell_path")]
            )
            + ":$PATH"
        )
        tf.write(f"export PATH={path_str}\n")
        tf.write(f"umask 0002\n")  # allow sharing by default
        tf.write("source /anysnake/code_venv/bin/activate\n")
        tf.write(bash_script)
        print("bash script running inside:\n", bash_script)
        print("")
        tf.flush()

        home_inside_docker = self.paths["home_inside_docker"]
        ro_volumes = [
            {
                "/anysnake/run.sh": tf.name,
                "/etc/passwd": "/etc/passwd",  # the users inside are the users outside
                "/etc/group": "/etc/group",
                "/etc/shadow": "/etc/shadow",
                "/anysnake/gosu": str(self.paths["bin"] / "gosu-amd64"),
            }
        ]
        rw_volumes = [
            {
                "/project": os.path.abspath("."),
                Path("~").expanduser(): self.paths["home_inside_docker"],
            }
        ]
        # for h in home_files:
        # p = Path("~").expanduser() / h
        # if p.exists():
        # if p.is_dir():
        # rw_volumes[0][str(p)] = str(Path(home_inside_docker) / h)
        # else:
        # target = str(Path(home_inside_docker) / h)
        # ro_volumes[0][target] = str(p)
        # for h in home_dirs:
        # p = Path("~").expanduser() / h
        # if p.exists() and not p.is_dir():
        # raise ValueError(f"Expected {p} to be a directory")
        # p.mkdir(exist_ok=True, parents=True)
        # target = str(Path(home_inside_docker) / h)
        # rw_volumes[0][target] = str(p)

        if allow_writes:
            rw_volumes.extend([df.volumes for df in self.strategies])
        else:
            ro_volumes.extend([df.volumes for df in self.strategies])
        rw_volumes.extend(
            [df.rw_volumes for df in self.strategies if hasattr(df, "rw_volumes")]
        )
        ro_volumes.append(volumes_ro)
        rw_volumes.append(volumes_rw)
        volumes = combine_volumes(ro=ro_volumes, rw=rw_volumes)
        cmd = ["docker", "run", "-it", "--rm"]
        for inside_path, (outside_path, mode) in sorted(
            volumes.items(), key=lambda x: str(x[1])
        ):
            if Path(outside_path).exists():
                cmd.append("-v")
                cmd.append("%s:%s:%s" % (outside_path, inside_path, mode))
        if not "HOME" in env:
            env["HOME"] = home_inside_docker
        for key, value in sorted(env.items()):
            cmd.append("-e")
            cmd.append("%s=%s" % (key, value))
        if py_spy_support:
            cmd.extend(
                [  # py-spy suppor"/home/u%i" % os.getuid()t
                    "--cap-add=SYS_PTRACE",
                    "--security-opt=apparmor:unconfined",
                    "--security-opt=seccomp:unconfined",
                ]
            )

        for from_port, to_port in self.ports:
            if from_port.endswith("+"):
                from_port = get_next_free_port(int(from_port[:-1]))
            cmd.extend(["-p", "%s:%s" % (from_port, to_port)])
        for from_port, to_port in ports:
            cmd.extend(["-p", "%s:%s" % (from_port, to_port)])

        cmd.extend(["--workdir", "/project"])
        cmd.append("--network=bridge")
        cmd.extend(
            [
                self.docker_image,
                "/anysnake/gosu",
                self.get_login_username(),
                "/bin/bash",
                "/anysnake/run.sh",
            ]
        )
        last_was_dash = True
        print("docker cmd")
        for x in cmd:
            if x.startswith("-") and not x.startswith("--"):
                print("  " + x, end=" ")
                last_was_dash = True
            else:
                if last_was_dash:
                    print(x, end=" \\\n")
                else:
                    print("  " + x, end=" \\\n")
                last_was_dash = False
        print("")
        return cmd, tf

    def run(self, *args, **kwargs):
        cmd, tf = self._build_cmd(*args, **kwargs)
        p = subprocess.Popen(cmd)
        p.communicate()

    def run_non_interactive(self, *args, **kwargs):
        cmd, tf = self._build_cmd(*args, **kwargs)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.communicate()

    def _run_docker(
        self, bash_script, run_kwargs, log_name, root=False, append_to_log=False
    ):
        docker_image = self.docker_image
        client = docker_from_env()
        tf = tempfile.NamedTemporaryFile(mode="w")
        volumes = {
            "/anysnake/run.sh": tf.name,
            "/etc/passwd": (
                "/etc/passwd",
                "ro",
            ),  # the users inside are the users outside
            "/etc/group": ("/etc/group", "ro"),
            # "/etc/shadow": ("/etc/shadow", 'ro'),
            "/anysnake/gosu": str(self.paths["bin"] / "gosu-amd64"),
            Path("~").expanduser(): self.paths["home_inside_docker"],
        }
        volumes.update(run_kwargs["volumes"])
        volume_args = {}
        for k, v in volumes.items():
            k = str(Path(k).absolute())
            if isinstance(v, tuple):
                volume_args[str(v[0])] = {"bind": str(k), "mode": v[1]}
            else:
                volume_args[str(v)] = {"bind": k, "mode": "rw"}
        run_kwargs["volumes"] = volume_args
        # print(run_kwargs["volumes"])
        # if not root and not "user" in run_kwargs:
        # run_kwargs["user"] = "%s:%i" % (self.get_login_username(), os.getgid())
        tf.write(f"umask 0002\n")  # allow sharing by default
        tf.write(bash_script)
        tf.flush()
        container = client.containers.create(
            docker_image,
            (
                ["/bin/bash", "/anysnake/run.sh"]
                if root
                else [
                    "/anysnake/gosu",
                    self.get_login_username(),
                    "/bin/bash",
                    "/anysnake/run.sh",
                ]
            ),
            **run_kwargs,
        )
        container_result = b""
        try:
            return_code = -1
            container.start()
            gen = container.logs(stdout=True, stderr=True, stream=True)
            for piece in gen:
                container_result += piece
                print(piece.decode("utf-8"), end="")
                sys.stdout.flush()
            return_code = container.wait()
        except KeyboardInterrupt:
            container.kill()

        if hasattr(log_name, "write"):
            log_name.write(container_result)
        elif log_name:
            if append_to_log:
                with open(str(self.paths[log_name]), "ab") as op:
                    op.write(container_result)
            else:
                self.paths[log_name].write_bytes(container_result)
        return return_code, container_result

    def build(
        self,
        # *,
        target_dir,
        target_dir_inside_docker,
        relative_check_filename,
        log_name,
        build_cmds,
        environment=None,
        additional_volumes=None,
        version_check=None,
        root=False,
    ):
        """Build a target_dir (into temp, rename on success),
        returns True if it was build, False if it was already present
        """
        target_dir = target_dir.absolute()
        if not target_dir.exists():
            if version_check is not None:
                version_check()
            print("Building", log_name[4:])
            build_dir = target_dir.with_name(target_dir.name + "_temp")
            if build_dir.exists():
                shutil.rmtree(str(build_dir))
            build_dir.mkdir(parents=True)
            volumes = {target_dir_inside_docker: build_dir}
            if additional_volumes:
                volumes.update(additional_volumes)
            container_result = self._run_docker(
                build_cmds,
                {"volumes": volumes, "environment": environment},
                log_name,
                root=root,
            )
            if not (Path(build_dir) / relative_check_filename).exists():
                if Path("logs").exists():
                    pass  # written in _run_docker
                else:
                    print("container stdout/stderr", container_result)
                raise ValueError(
                    "Docker build failed. Investigate " + str(self.paths[log_name])
                )
            else:
                # un-atomic copy (across device borders!), atomic rename -> safe
                build_dir.rename(target_dir)
            return True
        else:
            return False

    @property
    def major_python_version(self):
        p = self.python_version
        if p.count(".") == 2:
            return p[: p.rfind(".")]
        elif p.count(".") == 1:
            return p
        else:
            raise ValueError(
                f"Error parsing {self.anysnake.python_version} to major version"
            )

    def annotate_packages(self, parsed_packages):
        """Augment parsed packages with method"""
        parsed_packages = parsed_packages.copy()
        for name, entry in parsed_packages.items():
            if "/" in name:
                raise ValueError("invalid name: %s" % name)
            if not entry["version"]:
                entry["version"] = ""
            if entry["version"].startswith("hg+https"):
                entry["method"] = "hg"
                entry["url"] = entry["version"][3:]
            elif entry["version"].startswith("git+https"):
                entry["method"] = "hg"
                entry["url"] = entry["version"][3:]
            elif "/" in entry["version"]:
                if "://" in entry["version"]:
                    raise ValueError("Could not interpret %s" % entry["version"])
                entry["method"] = "git"
                entry["url"] = "https://github.com/" + entry["version"]
            else:
                entry["method"] = "pip"
        return parsed_packages

    @staticmethod
    def get_login_username():
        return pwd.getpwuid(os.getuid())[0]
