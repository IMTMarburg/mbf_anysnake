# -*- coding: future_fstrings -*-
import re
import requests
import subprocess
import time
import shutil
import time
from docker import from_env as docker_from_env
from pathlib import Path

re_github = r"[A-Za-z0-9-]+\/[A-Za-z0-9]+"


def combine_volumes(ro=[], rw=[]):
    d = dict()
    for (what, mode) in [(ro, "ro"), (rw, "rw")]:
        if isinstance(what, dict):
            what = [what]
        for dd in what:
            for target, source in dd.items():
                if isinstance(target, dict):
                    raise ValueError("fix me")
                elif isinstance(target, tuple):
                    raise ValueError("fix me")

                source = str(Path(source).absolute())
                d[target] = source, mode
    return d


def find_storage_path_from_other_machine(anysnake, postfix, check_func=None):
    """Find a usable storage path for this if it was already done by another machine
    and storage_per_hostname is set.
    Otherwise return the local storage_path / postfix
    """
    if check_func is None:
        check_func = lambda x: x.exists()
    search_path = anysnake.paths["storage"].parent.parent
    docker_image = Path(anysnake.paths["storage"].name)
    result = anysnake.paths["storage"] / postfix
    postfix = docker_image / postfix
    if not result.exists():
        if anysnake.storage_per_hostname:
            for d in search_path.glob("*"):
                if d.is_dir():
                    if check_func(d / postfix):
                        result = d / postfix
                        break
    return result


def download_file(url, filename):
    """Download a file with requests if the target does not exist yet"""
    if not Path(filename).exists():
        print("downloading", url, filename)
        r = requests.get(url, stream=True)
        if r.status_code != 200:
            raise ValueError(f"Error return on {url} {r.status_code}")
        start = time.time()
        count = 0
        with open(str(filename) + "_temp", "wb") as op:
            for block in r.iter_content(1024 * 1024):
                op.write(block)
                count += len(block)
        shutil.move(str(filename) + "_temp", str(filename))
        stop = time.time()
        print("Rate: %.2f MB/s" % ((count / 1024 / 1024 / (stop - start))))


def dict_to_toml(d):
    import tomlkit

    toml = tomlkit.document()
    toml.add(tomlkit.comment("Autogenertod by anysnake"))
    for key, sub_d in d.items():
        table = tomlkit.table()
        for k, v in sub_d.items():
            table.add(k, v)
        toml.add(key, table)
    return toml


def find_docker_ports():
    client = docker_from_env()
    res = set()
    for container in client.containers.list():
        for k, v in container.ports.items():
            if k.endswith("/tcp"):
                for x in v:
                    if "HostPort" in x:
                        res.add(int(x["HostPort"]))
    return res


def get_next_free_port(start_at):
    import socket

    try_next = True
    port = start_at
    docker_ports = find_docker_ports
    while try_next:
        try:
            if port in docker_ports:
                raise ValueError()
            s = socket.socket()
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("localhost", port))
            s.close()
            try_next = False
        except (socket.error, ValueError):
            port += 1
        if port > start_at + 100:
            raise ValueError("No empty port found within search range")
    return port


def clone_repo(url, name, target_path, log_file):
    print(f"]\tCloning {name} to {target_path} from {url}")
    if url.startswith("@"):
        url = url[1:]
    if re.match(re_github, url):
        method = "git"
        url = "https://github.com/" + url
    elif url.startswith("git+"):
        method = "git"
        url = url[4:]
    elif url.startswith("hg+"):
        method = "hg"
        url = url[3:]
    else:
        raise ValueError(
            "Could not parse url / must be git+http(s) / hg+https, or github path"
        )
    if method == "git":
        try:
            subprocess.check_call(
                ["git", "clone", url, str(target_path)],
                stdout=log_file,
                stderr=log_file,
            )
        except subprocess.CalledProcessError:
            import shutil

            shutil.rmtree(target_path)
            raise
    elif method == "hg":
        try:
            subprocess.check_call(
                ["hg", "clone", url, str(target_path)], stdout=log_file, stderr=log_file
            )
        except subprocess.CalledProcessError:
            import shutil

            if target_path.exists():
                shutil.rmtree(target_path)
            raise
