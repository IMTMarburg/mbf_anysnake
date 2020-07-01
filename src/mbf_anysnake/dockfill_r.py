# -*- coding: future_fstrings -*-

import re
from pathlib import Path
import requests
from .util import combine_volumes, find_storage_path_from_other_machine


class DockFill_R:
    def __init__(self, anysnake):
        self.anysnake = anysnake
        self.paths = self.anysnake.paths
        self.R_version = self.anysnake.R_version
        self.cran_mirror = self.anysnake.cran_mirror

        self.paths.update(
            {
                "storage_r": find_storage_path_from_other_machine(
                    self.anysnake, Path("R") / self.R_version
                ),
                "docker_storage_r": "/anysnake/R",
                "log_r": self.paths["log_storage"]
                / f"anysnake.R.{self.R_version}.log",
            }
        )
        self.volumes = {
            self.paths["docker_storage_r"]: self.paths["storage_r"]
        }
        self.shell_path = str(Path(self.paths["docker_storage_r"]) / "bin")

    def pprint(self):
        print(f"  R version={self.R_version}")

    def check_r_version_exists(self):
        if not re.match(r"\d+\.\d+\.\d", self.R_version):
            raise ValueError(
                "Incomplete R version specified - bust look like e.g 3.5.3"
            )
        url = self.cran_mirror + "src/base/R-" + self.R_version[0]
        r = requests.get(url).text
        if not f"R-{self.R_version}.tar.gz" in r:
            raise ValueError(
                (f"Unknown R version {self.R_version} - check {url} for list")
            )

    def ensure(self):
        # todo: switch to cdn by default / config in file
        r_url = (
            self.anysnake.cran_mirror
            + "src/base/R-"
            + self.anysnake.R_version[0]
            + "/R-"
            + self.anysnake.R_version
            + ".tar.gz"
        )
        return self.anysnake.build(
            target_dir=self.paths["storage_r"],
            target_dir_inside_docker=self.paths["docker_storage_r"],
            relative_check_filename="bin/R",
            log_name=f"log_r",
            additional_volumes={},
            version_check=self.check_r_version_exists(),
            build_cmds=f"""
cd ~
wget {r_url} -O R.tar.gz
tar xf R.tar.gz
cd R-{self.anysnake.R_version}
./configure --prefix={self.paths['docker_storage_r']} --enable-R-shlib --with-blas --with-lapack --with-x=no
make -j {self.anysnake.cores}
make install

echo "done"
""",
        )


class DockFill_Rpy2:
    def __init__(self, anysnake, dockfill_py, dockfill_r):
        self.anysnake = anysnake
        self.paths = self.anysnake.paths
        self.python_version = self.anysnake.python_version
        self.R_version = self.anysnake.R_version
        self.rpy2_version = self.anysnake.rpy2_version
        self.dockfill_python = dockfill_py
        self.dockfill_r = dockfill_r

        self.paths.update(
            {
                "storage_rpy2": (
                    find_storage_path_from_other_machine(
                        self.anysnake,
                        Path("rpy2") / f"py={self.python_version}_r={self.R_version}_rpy2={self.rpy2_version}",
                    )
                ),
                "docker_storage_rpy2": "/anysnake/rpy2",
                "log_rpy2": self.paths["log_storage"]
                / f"anysnake.rpy2.{self.python_version}-{self.R_version}.log",
            }
        )
        self.volumes = {
            self.paths["docker_storage_rpy2"]: self.paths["storage_rpy2"]
        }
        self.env = {'LD_LIBRARY_PATH': "/anysnake/R/lib/R/lib"}

    def pprint(self):
        pass

    def ensure(self):
        # TODO: This will probably need fine tuning for combining older Rs and the
        # latest rpy2 version that supported them
        return self.anysnake.build(
            target_dir=self.paths["storage_rpy2"],
            target_dir_inside_docker=self.paths["docker_storage_rpy2"],
            relative_check_filename=f"lib/python{self.anysnake.major_python_version}/site-packages/rpy2/__init__.py",
            log_name=f"log_rpy2",
            additional_volumes=combine_volumes(
                ro=[self.dockfill_python.volumes, self.dockfill_r.volumes]
            ),
            build_cmds=f"""

export R_HOME={self.paths['docker_storage_r']}
export PATH={self.paths['docker_storage_r']}/bin:$PATH
# use the (hopefully more robust) API mode rpy2
export RPY2_CFFI_MODE=API
{self.paths['docker_storage_python']}/bin/virtualenv -p {self.paths['docker_storage_python']}/bin/python {self.paths['docker_storage_rpy2']}
mkdir /tmp/rpy2
cd /tmp/rpy2
{self.paths['docker_storage_rpy2']}/bin/pip3 download rpy2=={self.rpy2_version}
#this might not be enough later on, if rpy2 gains a version that is
# dependend on something we don't get as a wheel
{self.paths['docker_storage_rpy2']}/bin/pip3 install *.whl
tar xf rpy2-*.tar.gz
rm rpy2-*.tar.gz
mv rpy2* rpy2
cd rpy2
{self.paths['docker_storage_rpy2']}/bin/pip install .

{self.paths['docker_storage_rpy2']}/bin/pip install tzlocal
touch {self.paths['docker_storage_rpy2']}/done
chown 1001 {self.paths['docker_storage_rpy2']} -R
echo "done"
""",
        )
