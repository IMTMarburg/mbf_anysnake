# -*- coding: future_fstrings -*-
from pathlib import Path
import subprocess
import docker
import tempfile
import shutil
import os


def copytree(src, dst, symlinks=False, ignore=None):
    """Since shutil.copytree insists that the directory must not exist
    exist. Does not honor symlinks or ignore in top directory"""
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


class DockFill_Docker:
    def __init__(self, anysnake, docker_build_cmds=""):
        self.anysnake = anysnake
        self.paths = self.anysnake.paths
        self.paths.update(
            {
                "docker_image_build_scripts": (
                    Path(__file__).parent / "docker_images"
                )
            }
        )
        self.docker_build_cmds = docker_build_cmds
        self.volumes = {}

    def get_dockerfile_text(self, docker_image_name):
        b = (
            self.paths["docker_image_build_scripts"] / docker_image_name / "Dockerfile"
        ).read_text()
        for s in self.anysnake.strategies:
            if hasattr(s, "get_additional_docker_build_cmds"):
                b += s.get_additional_docker_build_cmds()
        b += "\n" + self.docker_build_cmds + "\n"
        return b

    def ensure(self):
        """Build (or pull) the docker container if it's not present in the system.
        pull only happens if we don't have a build script
        """
        client = docker.from_env()
        tags_available = set()
        for img in client.images.list():
            tags_available.update(img.tags)
        if self.anysnake.docker_image in tags_available:
            pass
        else:
            docker_image = self.anysnake.docker_image[
                : self.anysnake.docker_image.rfind(":")
            ]
            bs = self.paths["docker_image_build_scripts"] / docker_image / "build.sh"
            if bs.exists():
                with tempfile.TemporaryDirectory() as td:
                    copytree(str(bs.parent), td)
                    df = Path(td) / "Dockerfile"
                    df.chmod(0o644)
                    df.write_text(self.get_dockerfile_text(docker_image))
                    print("having to call", bs)
                    print(os.listdir(td))
                    subprocess.check_call(["./build.sh"], cwd=str(td))
            else:
                # print(bs, "not found")
                client.images.pull(self.anysnake.docker_image)
        return False

    def pprint(self):
        print(f"  docker_image = {self.anysnake.docker_image}")

    def get_dockerfile_hash(self, docker_image_name):
        import hashlib

        dockerfile = ()
        hash = hashlib.md5()
        try:
            hash.update(self.get_dockerfile_text(docker_image_name).encode("utf-8"))
        except FileNotFoundError:
            pass
        try:
            hash.update(
                (
                    self.paths["docker_image_build_scripts"]
                    / docker_image_name
                    / "sudoers"
                ).read_bytes()
            )
        except FileNotFoundError:
            pass

        tag = hash.hexdigest()
        return tag
