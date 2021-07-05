# -*- coding: future_fstrings -*-
import re
import os
from pathlib import Path
from .anysnake import Anysnake
import tomlkit


def merge_config(d1, d2):
    result = d1.copy()
    for key in d2:
        if not key in result:
            result[key] = {}
        for key2 in d2[key]:
            result[key][key2] = d2[key][key2]
    return result


def replace_env_vars(s):
    for k, v in os.environ.items():
        s = s.replace("${%s}" % (k,), v)
    return s


def parse_requirements(req_file):
    """Parse the requirements from a anysnake.toml file
    See readme.

    """
    used_files = [str(Path(req_file).absolute())]
    with open(req_file) as op:
        p = tomlkit.loads(op.read())
    if "base" in p and "global_config" in p["base"]:
        fn = replace_env_vars(p["base"]["global_config"])
        with open(fn) as op:
            gconfig = tomlkit.loads(op.read())
            used_files.insert(0, p["base"]["global_config"])
            p = merge_config(gconfig, p)

    paths = [("base", "storage_path")]
    if "env" in p:
        for k in p["env"]:
            if isinstance(p["env"][k], str):
                paths.append(("env", k))
    for path in paths:
        if path[0] in p:
            if path[1] in p[path[0]]:
                p[path[0]][path[1]] = replace_env_vars(p[path[0]][path[1]])
    p["used_files"] = used_files
    return p


def verify_port(port_def):
    """verify that a port definied in anysnake.toml looks like
    1243
    1234+ ( search next free port)
    1234+:4567 (external/internal port)
    """
    if re.match(r"^\d+\+?$", str(port_def)):
        port_def = str(port_def), str(port_def).replace("+", "")
    elif re.match(r"^(\d+\+?):(\d+)$", str(port_def)):
        port_def = tuple(re.findall("(\d+\+?):(\d+)", str(port_def))[0])
    else:
        raise ValueError(f"invalid port def '{port_def}'")
    return port_def


def parsed_to_anysnake(parsed):
    if not "base" in parsed:
        raise ValueError("no [base] in configuration")
    base = parsed["base"]

    if "project_name" in parsed["base"]:
        project_name = parsed["base"]
    else:
        project_name = Path(parsed["used_files"][0]).parent.name

    if not "python" in base or not base["python"]:
        raise ValueError(
            "Must specify at the very least a python version to use, e.g. python==3.7"
        )
    python_version = base["python"]

    if "docker_image" in base:
        if ":" in base["docker_image"]:
            docker_image = base["docker_image"]
        else:
            docker_image = base["docker_image"] + ":%md5sum%"
    else:
        docker_image = "mbf_anysnake_18.04:%md5sum%"

    if "bioconductor" in base:
        bioconductor_version = base["bioconductor"]
    else:
        bioconductor_version = None
    R_version = base.get("R", None)
    rpy2_version = base.get("rpy2_version", "3.2.0")

    if "storage_path" in base:
        storage_path = Path(base["storage_path"])
    else:
        storage_path = Path("version_store")
    storage_per_hostname = bool(base.get("storage_per_hostname", False))

    post_build_cmd = parsed.get("build", {}).get("post_storage_build", False)
    if not isinstance(post_build_cmd, str) and not post_build_cmd is False:
        raise ValueError("post_storage_build must be a string")

    if "code_path" in base:
        code_path = Path(base["code_path"])
        del base["code_path"]
    else:
        code_path = Path("code")
    if "code_path_docker" in base:
        code_path_docker = Path(base["code_path_docker"])
        if not code_path_docker.is_absolute():
            code_path_docker = Path("/project") / code_path_docker
        del base["code_path_docker"]
    else:
        code_path_docker = Path("/project/code")

    # Todo: make configurable
    Path("logs").mkdir(parents=False, exist_ok=True)

    additional_pip_lookup_res = list((parsed.get("pip_regexps", {})).items())
    additional_pip_lookup_res.append(
        ("^@gh/([^/]+)/(.+)", r"@git+https://github.com/\1/\2")
    )
    global_pip_packages = parsed.get("global_python", {})
    local_pip_packages = parsed.get("python", {})
    check_pip_definitions(global_pip_packages, additional_pip_lookup_res)
    check_pip_definitions(local_pip_packages, additional_pip_lookup_res)
    bioconductor_whitelist = base.get("bioconductor_whitelist", [])
    if not isinstance(bioconductor_whitelist, list):
        raise ValueError("bioconductor_whitelist must be a list")
    cran_mode = base.get("cran", "full")
    if not cran_mode in ("minimal", "full"):
        raise ValueError("cran must be one of ('full', 'minimal')")

    environment_variables = parsed.get("env", {})

    rust_versions = parsed.get("base", {}).get("rust", [])
    if bioconductor_version and not "1.30.0" in rust_versions:  # TODO: refactor
        rust_versions.append("1.30.0")
    cargo_install = parsed.get("cargo_install")

    ports = [verify_port(x) for x in parsed.get("base", {}).get("ports", [])]

    docker_build_cmds = parsed.get("base", {}).get("docker_build_cmds", "")

    global_clones = parsed.get("global_clones", {})
    local_clones = parsed.get("local_clones", {})
    check_pip_definitions(global_clones, additional_pip_lookup_res)
    check_pip_definitions(local_clones, additional_pip_lookup_res)

    if "per_user" in base:
        per_user = Path(base["per_user"])
    else:
        per_user = None

    return Anysnake(
        project_name=project_name,
        docker_image=docker_image,
        python_version=python_version,
        bioconductor_version=bioconductor_version,
        r_version=R_version,
        rpy2_version=rpy2_version,
        global_python_packages=global_pip_packages,
        local_python_packages=local_pip_packages,
        bioconductor_whitelist=bioconductor_whitelist,
        cran_mode=cran_mode,
        storage_path=storage_path,
        storage_per_hostname=storage_per_hostname,
        code_path=code_path,
        code_path_docker=code_path_docker,
        environment_variables=environment_variables,
        post_build_cmd=post_build_cmd,
        rust_versions=rust_versions,
        cargo_install=cargo_install,
        ports=ports,
        docker_build_cmds=docker_build_cmds,
        global_clones=global_clones,
        local_clones=local_clones,
        per_user=per_user,
    )


def check_pip_definitions(defs, pip_lookup_regexps):
    for k, v in defs.items():
        for rex, replacement in pip_lookup_regexps:
            if re.match(rex, v):
                if isinstance(replacement, str):
                    defs[k] = re.sub(rex, replacement, v)
                else:
                    defs[k] = replacement[0].replace("\\1", k)

    for k, v in defs.items():
        if not re.match(
            "^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", k, flags=re.IGNORECASE
        ):
            raise ValueError(
                f"Python package name did not match PEP-0508 Names regexps: {k}"
            )
        if v and v[0] != "@":
            operators = ["<=", "<", "!=", "==", ">=", ">", "~=", "==="]
            r = r"^(" + "|".join(operators) + r")?([A-Za-z0-9_.*+!-]+)"
            if not re.match(r, v):
                raise ValueError(
                    f"Invalid version specification '{k}' = '{v}' - See PEP-0508"
                )
            if "/" in v:
                raise ValueError(
                    f"Invalid version specification - urls must start with @: '{k}' = '{v}' "
                )
