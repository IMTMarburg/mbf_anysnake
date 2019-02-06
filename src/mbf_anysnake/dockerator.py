# -*- coding: future_fstrings -*-

from pathlib import Path
from docker import from_env as docker_from_env
import time
import tempfile
import shutil
import requests
import subprocess
import re
import pprint
import packaging.version
import os
import multiprocessing


from .dockfill_docker import DockFill_Docker
from .dockfill_python import DockFill_Python, DockFill_GlobalVenv, DockFill_CodeVenv
from .dockfill_r import DockFill_R, DockFill_CRAN, DockFill_Rpy2
from .dockfill_bioconductor import DockFill_Bioconductor
from .util import combine_volumes


class Dockerator:
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
        docker_image,
        python_version,
        bioconductor_version,
        r_version,
        global_python_packages,
        local_python_packages,
        cran_packages,
        storage_path,
        code_path,
        cores=None,
        cran_mirror="https://cloud.r-project.org",
    ):
        self.cores = cores if cores else multiprocessing.cpu_count()
        self.cran_mirror = cran_mirror
        if not self.cran_mirror.endswith("/"):
            self.cran_mirror += "/"

        self.storage_path = Path(storage_path)
        if not self.storage_path.exists():
            raise IOError(f"{self.storage_path} did not exist")
        storage_path = storage_path / docker_image.replace(":", "-")
        code_path = Path(code_path)
        code_path.mkdir(parents=False, exist_ok=True)

        self.docker_image = docker_image
        self.python_version = python_version
        self.bioconductor_version = bioconductor_version
        self.global_python_packages = global_python_packages
        self.local_python_packages = local_python_packages
        self.cran_packages = cran_packages

        self.paths = {
            "storage": storage_path,
            "code": code_path,
            "log_storage": storage_path / "logs",
            "log_code": code_path / "logs",
        }
        self.paths["storage"].mkdir(exist_ok=True)
        self.paths["log_storage"].mkdir(parents=False, exist_ok=True)
        self.paths["log_code"].mkdir(parents=False, exist_ok=True)

        dfp = DockFill_Python(self)
        self.strategies = [
            DockFill_Docker(self),
            dfp,
            DockFill_CodeVenv(self, dfp),  # since I want them earlier in the path!
            DockFill_GlobalVenv(self, dfp),
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
            self.strategies.append(DockFill_CRAN(self, dfr))
            if self.bioconductor_version:
                self.strategies.append(DockFill_Bioconductor(self, dfr))

        for k, v in self.paths.items():
            self.paths[k] = Path(v)

    def pprint(self):
        print("Dockerator")
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
        for s in self.strategies:
            start = time.time()
            s.ensure()
            if do_time:
                print(s.__class__.__name__, time.time() - start)

    def run(
        self,
        bash_script,
        env={},
        ports={},
        py_spy_support=True,
        home_files={},
        volumes_ro={},
        volumes_rw={},
        allow_writes=False,
    ):
        env = env.copy()

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
        tf.write(bash_script)
        tf.flush()

        home_inside_docker = "/home/u%i" % os.getuid()
        ro_volumes = [{tf.name: "/opt/run.sh"}]
        rw_volumes = [{os.path.abspath("."): "/project"}]
        for h in home_files:
            p = Path("~").expanduser() / h
            if p.exists():
                if p.is_dir():
                    rw_volumes[0][str(p)] = str(Path(home_inside_docker) / h)
                else:
                    ro_volumes[0][str(p)] = str(Path(home_inside_docker) / h)

        if allow_writes:
            rw_volumes.extend([df.volumes for df in self.strategies])
        else:
            ro_volumes.extend([df.volumes for df in self.strategies])
        ro_volumes.append(volumes_ro)
        rw_volumes.append(volumes_rw)
        volumes = combine_volumes(ro=ro_volumes, rw=rw_volumes)

        cmd = ["docker", "run", "-it"]
        for outside_path, v in volumes.items():
            inside_path, mode = v
            cmd.append("-v")
            cmd.append("%s:%s:%s" % (outside_path, inside_path, mode))
        if not "HOME" in env:
            env["HOME"] = home_inside_docker
        for s in self.strategies:
            if hasattr(s, "shell_envs"):
                env.update(s.shell_envs)
        for key, value in env.items():
            cmd.append("-e")
            cmd.append("%s=%s" % (key, value))
        cmd.append("-u")
        cmd.append("u%i" % os.getuid())
        if py_spy_support:
            cmd.extend(
                [  # py-spy suppor"/home/u%i" % os.getuid()t
                    "--cap-add=SYS_PTRACE",
                    "--security-opt=apparmor:unconfined",
                    "--security-opt=seccomp:unconfined",
                ]
            )

        for from_port, to_port in ports:
            cmd.extend(["-p", "%s:%s" % (from_port, to_port)])

        cmd.extend(["-w", "/project"])
        cmd.extend([self.docker_image, "/bin/bash", "/opt/run.sh"])
        # pprint.pprint(cmd)
        p = subprocess.Popen(cmd)
        p.communicate()

    def _run_docker(
        self, bash_script, run_kwargs, log_name, root=False, append_to_log=False
    ):
        docker_image = self.docker_image
        run_kwargs["stdout"] = True
        run_kwargs["stderr"] = True
        client = docker_from_env()
        tf = tempfile.NamedTemporaryFile(mode="w")
        volumes = {tf.name: "/opt/run.sh"}
        volumes.update(run_kwargs["volumes"])
        volume_args = {}
        for k, v in volumes.items():
            k = str(Path(k).absolute())
            if isinstance(v, tuple):
                volume_args[k] = {"bind": str(v[0]), "mode": v[1]}
            else:
                volume_args[k] = {"bind": str(v), "mode": "rw"}
        # pprint.pprint(volume_args)
        run_kwargs["volumes"] = volume_args
        if not root and not "user" in run_kwargs:
            run_kwargs["user"] = "%i:%i" % (os.getuid(), os.getgid())
        tf.write(bash_script)
        tf.flush()
        container_result = client.containers.run(
            docker_image, "/bin/bash /opt/run.sh", **run_kwargs
        )
        if hasattr(log_name, "write"):
            log_name.write(container_result)
        elif log_name:
            if append_to_log:
                if not self.paths[log_name].exist():
                    mode = 'wb'
                else:
                    mode = 'ab'
                with open(self.paths[log_name], mode) as op:
                    op.write(container_result)
            else:
                self.paths[log_name].write_bytes(container_result)
        return container_result

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
        target_dir = target_dir.absolute()
        if not target_dir.exists():
            if version_check is not None:
                version_check()
            print("Building", log_name[4:])
            build_dir = target_dir.with_name(target_dir.name + "_temp")
            if build_dir.exists():
                shutil.rmtree(build_dir)
            build_dir.mkdir(parents=True)
            volumes = {build_dir: target_dir_inside_docker}
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

    @property
    def major_python_version(self):
        p = self.python_version
        if p.count(".") == 2:
            return p[: p.rfind(".")]
        elif p.count(".") == 1:
            return p
        else:
            raise ValueError(
                f"Error parsing {self.dockerator.python_version} to major version"
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