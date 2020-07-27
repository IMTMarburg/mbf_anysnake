# *- coding: future_fstrings -*-
import subprocess
import sys
import logging
import requests
import shutil
import os
import re
from pathlib import Path
import packaging.version
import pypipegraph as ppg

# some packages are *duplicated* in the package index.
# the default is, if the version is identical, to take the one with a md5sum.
# otherwise the valid options are first, last, larger (=version) and smaller
# (=version)
duplicate_handling = {
    "cran": {
        "survival": "larger",
        "sivipm": "first",  # 1.1-3 and 1.1-4, but 1.1-4 has no tar.gz!
        "mgcv": "larger",
	'cluster': 'larger',
        # "boot": "last",
    }
}
blacklist = {
    "rLindo",  # - needs some properietary api
    "BRugs",  # - needs openbugs, no ubuntu package?
    "Rcplex",  # needs properietary package
    "cplexAPI",  # needs properietary package
    "Rmosek",  # no package in ubuntu repository
    "ROracle",  # not sure what package is necessary
    "rgeos",  # incompatible with libgeos in ubuntu 18.04
    "rsbml",  # can't find libsmbl - possibly fixable
    "xps",  # needs libroot-core-dev, no longer in ubuntu 18.04
    "gpuR",  # unknown opencl error - possibly fixable
    "cudaBayesreg",  # won't compile, removed from cran on mantainer's request
    "permGPU",  # insists on not respecting CUDA_HOME enviroment variable.
    "BiocSklearn",  # won't use the right python? possible fixable
    "rPython",  # can't find python so - fixable?
    "SnakeCharmR",  # can't find python so - fixable?
    # windows only packages are automatically detected
}
packages_needing_X = {
    #  unfortunatly, these can not be auto detected by looking
    # for tcltk - some packages needing tcltk install just fine
    "cairoDevice",
    "rpanel",
    "GroupSeq",
    "HierO",
    "HomoPolymer",  # - seems to compile, but crashes on GDK call
    "gWidgets2tcltk",
    "gWidgetstcltk",
    "iplots",
    "loon",
    "MSeasyTkGUI",
    "TTAinterfaceTrendAnalysis",
    "soptdmaeA",  # incompatible tk version
    "qtbase",  # needs qt - qt needs X, I presum
    "rMouse",
    "optrcdmaeAT",
    "optbdmaeAT",
    "JFE",
}
blacklist.update(packages_needing_X)
blacklist_per_version = {
    "3.6": {
        "RWekajars",  # java version - possibly fixable
        "bgx",  # won't compile?
        "rstan",  # won't compile?
        "bigmemoryExtras",  # incompatible bigmemory version?
        "MSGFplus",  # apperantly can't evaluate java version - possibly fixable
        "rTANDEM",  # invalid c++
        "psichomics",  # incompatible with Rcpp package installed
        "beachmat",  # incompatible with Rcpp package installed
    },
    "3.7": {
        "bgx",  # won't compile?
        "MSGFplus",  # apperantly can't evaluate java version - possibly fixable
        "rTANDEM",  # invalid c++
        "pathifier",  # incompatible princurve version
        "ClusterSignificance",  # incompatible princurve version
        "ggtree",  # incompatible ggplot version
        "ggcyto",  # incompatible ggplot version
    },
    "3.8": {
        # "GEOquery",  # geoquery needs redr 1.3.1 which was released two months *after* bioconductor 3.8 - manual overwrite
        # "ggtree",  # requests tidytree >=0.1.9 but only 0.2.0 released a month later exports the necessary function - manual overwrite
        "rTANDEM",  # invalid c++
        "bgx",  # won't compile?
        "MSGFplus",  # apperantly can't evaluate java version - possibly fixable
        "KoNLP",  # some kind of scala/java version change? msising value where TRUE/FALSE needed
        "flipflop",  # won't compile
        "dSimer",  # won't compile
    },
    "3.10": {
        'tseries', # compilation problem - cfuncs.mod not found?
        'frailtypack',# compilation problem - comon.mod not found?
        'brainGraph', # summary.mediate is not exported by 'namespace:mediation'
        'kerasR',   # needs installed python module?
        'kmcudaR', # compilation issue?
        'pbdSLAP', # I have no idea
        'phateR',  # hardcoded python?
        'PythonInR', # missing python.h? huh? python3|
        'QuantLib', # missing header?
        'RQuantLib', 
        'mlm4omics', # boost error?
        'MSGFplus', # who knows
        'Rcwl', # missing cwltool
        'laGP',  # compilation issue
        'KoNLP', # compilation issue
        'sdcMicro',  # can't download?
        'Rmagic',  # can't download?

        'MoonlightR', # needs logicReg which was not in cran at that timepoint
        'MSGFplus', # some issue detecting java version?
        'Rcwl', # needs cwltoolo
        'Rhisat2', # build falirue
        'bioCancer', # xml too old
        'plyranges',  #needs newer tidyselect than at the point of bioconductor release 
        'splatter', #needs newer checkmate than at the point of bioconductor release
        'trio', # needs logicReg

        'animalcules', #??
        'chroGPS', #??
        'logicFS', #??
        'readat',#??
        'sesame',#??


       }
}

manual_dependencies = {  # because the cran annotation sometimes simply is wrong
    "ForecastComb": ["foreign"],
    "latticeDensity": ["lattice"],
    "cudaBayes": ["Rcpp"],
}

manual_overwrite = {
    "3.8": {
        "cran": {
            "readr": "https://mran.microsoft.com/snapshot/2018-12-23/src/contrib/readr_1.3.1.tar.gz",
            # GEOQuery needs a readr that was realeased 2 months after the bioconductor release?!
            "tidytree": "https://cran.microsoft.com/snapshot/2018-12-01/src/contrib/tidytree_0.2.0.tar.gz",
            # requests tidytree >=0.1.9 but only 0.2.0 released a month later exports the necessary function - manual overwrite}
        }
    }
}


build_in = {
    "R",
    "base",
    "boot",
    "class",
    "cluster",
    "codetools",
    "compiler",
    "datasets",
    "foreign",
    "graphics",
    "grDevices",
    "grid",
    "KernSmooth",
    "lattice",
    "MASS",
    "Matrix",
    "methods",
    "mgcv",
    "nlme",
    "nnet",
    "parallel",
    "rpart",
    "spatial",
    "splines",
    "stats",
    "stats4",
    "survival",
    "tcltk",
    "tools",
    "utils",
}


def install_bioconductor():
    bc_version = os.environ["BIOCONDUCTOR_VERSION"]
    cran_mode = os.environ["CRAN_MODE"]
    sources = ["cran", "software", "annotation", "experiment"]
    sources = {
        x: load_packages(x, os.environ["URL_%s" % x.upper()]).get() for x in sources
    }
    if bc_version in manual_overwrite:
        for src_name, src in manual_overwrite[bc_version].items():
            for pkg_name, url in src.items():
                sources[src_name][pkg_name]["url"] = url

    pkgs = list(sources.values())

    whitelist = os.environ["BIOCONDUCTOR_WHITELIST"].split(":")

    logging.basicConfig(
        filename="/anysnake/bioconductor/ppg.log", level=logging.INFO, filemode="w"
    )
    cpus = int(ppg.util.CPUs() * 1.25)  # rule of thumb to achieve maximum throughupt
    ppg.new_pipegraph(
        invariant_status_filename="/anysnake/bioconductor/.ppg_status",
        resource_coordinator=ppg.resource_coordinators.LocalSystem(
            max_cores_to_use=cpus, interactive=False
        ),
    )
    jobs, prune_because_of_missing_preqs = build_jobs(pkgs)
    # now we have jobs for *every* R package
    # which we now need to filter down

    to_prune = set()
    to_prune.update(sources["annotation"].keys())
    to_prune.update(sources["experiment"].keys())
    to_prune.update(prune_because_of_missing_preqs)
    prune(jobs, to_prune)

    if cran_mode == "minimal":
        prune(jobs, sources["cran"])
        already_unpruned = set()
        for k in sources["software"]:
            for j in jobs[k]:
                unprune(j, already_unpruned)
        prune(jobs, to_prune)

    already_unpruned = set()
    for k in whitelist:
        if k in jobs:
            for j in jobs[k]:
                unprune(j, already_unpruned)
    if "_full_" in whitelist:
        for k in sources["software"]:
            for j in jobs[k]:
                unprune(j, already_unpruned)

    # still need to apply the blacklist, no matter whether __full__ was set!
    to_prune = set()
    to_prune.update(windows_only_packages(pkgs))
    to_prune.update(blacklist)
    if bc_version in blacklist_per_version:
        to_prune.update(blacklist_per_version[bc_version])
    prune(jobs, to_prune)

    ppg.util.global_pipegraph.connect_graph()
    ppg.run_pipegraph()
    for j in ppg.util.global_pipegraph.job_uniquifier.values():
        if j._pruned:
            print("pruned", j.job_id, "because of", j._pruned)
    write_done_sentinel(cran_mode, whitelist)


def prune(jobs, to_prune):
    for k in to_prune:
        if k in jobs:
            for j in jobs[k]:  # download and install job.
                j.prune()


def unprune(job, seen):
    if not job.job_id in seen:
        seen.add(job.job_id)
        job._pruned = False
        for p in job.prerequisites:
            unprune(p, seen)


def windows_only_packages(pkgs):
    """Find out which packages are windows only"""
    res = set()
    for p in pkgs:
        for name, info in p.items():
            if info.get("OS_type", "").lower() == "windows":
                res.add(name)
    return res


def load_packages(name, url):
    """load the package info from disk"""
    fn = "/anysnake/bioconductor_download/%s.PACKAGES" % name
    info = RPackageInfo(url, name, fn)
    return info


def write_done_sentinel(cran_mode, whitelist):
    Path("/anysnake/bioconductor/done.sentinel").write_text(
        "done:" + cran_mode + ":" + ":".join(sorted(whitelist))
    )


def get_preqs(info):
    for d in ["Depends", "Imports", "LinkingTo"]:
        for preq in info[d]:
            yield preq
        if info["name"] in manual_dependencies:
            for preq in manual_dependencies[info["name"]]:
                yield preq


def build_jobs(pkgs):
    """Build the package download & install jobs"""
    jobs = {}
    for p in pkgs:
        items = list(p.items())  # mix it up
        # random.shuffle(items)
        for name, info in items:
            if not name in build_in:
                download_job = job_download(info)
                install_job = job_install(info)
                install_job.depends_on(download_job)
                jobs[name] = [download_job, install_job]

    prune_because_of_missing_preqs = set()
    for p in pkgs:
        for name, info in p.items():
            for preq in get_preqs(info):
                if preq not in build_in:
                    if preq in jobs:
                        jobs[name][-1].depends_on(jobs[preq][-1])
                    else:
                        print(
                            f"Missing preq {preq} for {name} - pkg not in repositories. Pruning"
                        )
                        prune_because_of_missing_preqs.add(name)
    return jobs, prune_because_of_missing_preqs


def job_download(info):
    """Download the package defined in info"""
    target_fn = f'/anysnake/bioconductor_download/{info["repo"]}/{info["name"]}_{info["version"]}.tar.gz'

    def download():
        p = Path(target_fn)
        p.parent.mkdir(exist_ok=True, parents=False)
        r = requests.get(info["url"], stream=True)
        if r.status_code != 200:
            raise ValueError("Error return on %s %s " % (info["url"], r.status_code))
        with open(str(target_fn) + "_temp", "wb") as op:
            for block in r.iter_content(1024 * 1024):
                op.write(block)
        shutil.move(str(target_fn) + "_temp", str(target_fn))

    job = ppg.TempFileGeneratingJob(target_fn, download)
    job.ignore_code_changes()
    return job


def job_install(info):
    """install the package defined in info"""
    sentinel_file = Path(
        "/anysnake/bioconductor/%s/%s.sentinel" % (info["name"], info["name"])
    )

    def do():
        R_cmd = ["/anysnake/R/bin/R", "--no-save"]
        r_build_script = """

        lib = "/anysnake/bioconductor/"
        .libPaths(c(lib, .libPaths()))

        #some packages need python - let's give em a virtualenv...
        if (%s)
        {
            if (requireNamespace("reticulate"))
            {
                library(reticulate)
                use_python("/anysnake/python/bin/python")
                use_virtualenv("/anysnake/storage_venv")
            }
        }
        print(Sys.getenv())
        install.packages("/anysnake/bioconductor_download/%s/%s_%s.tar.gz",
                lib=lib,
                repos=NULL,
                type='source',
                install_opts = c('--no-docs', '--no-multiarch')
                )
        write("done", "%s" )
        """ % (
            "T" if "reticulte" in get_preqs(info) else "F",
            info["repo"],
            info["name"],
            info["version"],
            str(sentinel_file),
        )
        # tf = tempfile.NamedTemporaryFile(suffix=".r")
        target_dir = Path("/anysnake/bioconductor") / info["name"]
        target_dir.mkdir(exist_ok=True)
        tf = target_dir / "rinstall.r"
        tf.write_bytes(r_build_script.encode("utf-8"))
        # tf.flush()
        # tf.seek(0, 0)
        env = os.environ.copy()
        env[
            "R_DONT_USE_TK"
        ] = "true"  # otherwise the tk package will loop endlessly on modern linux
        env["R_LIBS_SITE"] = "/anysnake/bioconductor"
        env["R_LIBS_USER"] = ""
        env["PATH"] = ":".join(env["PATH"].split(":") + ["/anysnake/R/bin"])
        env["PYTHONPATH"] = ":".join(
            env.get("PYTHONPATH", "").split(":") + [x for x in sys.path if x]
        )
        env["LIBRARY_PATH"] = ":".join(
            env.get("LIBRARY_PATH", "").split(":") + ["/dockeractor/python/lib"]
        )
        env["LD_LIBRARY_PATH"] = ":".join(
            env.get("LD_LIBRARY_PATH", "").split(":") + ["/dockeractor/python/lib"]
        )
        env["MAKEFLAGS"] = "-j %i" % (ppg.util.CPUs(),)

        p = subprocess.Popen(
            " ".join(R_cmd),
            shell=True,
            stdin=open(tf),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        stdout, stderr = p.communicate()
        target_dir_existed = target_dir.exists()
        target_dir.mkdir(exist_ok=True)
        tf.write_bytes(r_build_script.encode("utf-8"))
        (target_dir / "stdout").write_bytes(stdout)
        (target_dir / "stderr").write_bytes(stderr)
        if p.returncode != 0 or not target_dir_existed:
            print(stdout)
            print(stderr)
            raise ValueError("R error return code")
        else:
            pass  # sentinel file get's written by R upon completion

    job = ppg.FileGeneratingJob(sentinel_file, do)
    job.ignore_code_changes()
    return job


class RPackageInfo:
    """Caching parser for CRAN style packages lists"""

    def __init__(self, base_url, name, cache_filename):
        self.base_url = base_url
        self.name = name
        self.cache_filename = Path(cache_filename)

    def get(self):
        """Return a dictionary:
        package -> depends, imports, suggests, version
        """
        if not hasattr(self, "_packages"):
            raw = self.cache_filename.read_text()
            pkgs = {}
            errors = []
            for p in self.parse(raw):
                p["name"] = p["Package"]
                for x in ("Depends", "Suggests", "Imports", "LinkingTo"):
                    p[x.lower()] = set(p[x]) - build_in
                p["version"] = p["Version"] if p["Version"] else ""
                p["url"] = (
                    self.base_url
                    + "src/contrib/"
                    + p["name"]
                    + "_"
                    + p["version"]
                    + ".tar.gz"
                )
                p["repo"] = self.name
                if p["name"] in pkgs:
                    what_to_do = duplicate_handling.get(self.name, {}).get(
                        p["name"], "with_md5"
                    )
                    if what_to_do == "last":
                        pkgs[p["name"]] = p
                    elif what_to_do == "first":
                        pass
                    elif what_to_do == "smaller" or what_to_do == "larger":
                        v1 = parse_version(pkgs[p["name"]]["version"])
                        v2 = parse_version(p["version"])
                        if what_to_do == "smaller":
                            if v1 < v2:
                                pass
                            else:
                                pkgs[p["name"]] = p
                        else:
                            if v1 < v2:
                                pkgs[p["name"]] = p
                            else:
                                pass
                    elif what_to_do == "with_md5":
                        if p["version"] == pkgs[p["name"]]["version"]:
                            if "MD5sum" in p:
                                pkgs[p["name"]] = p
                            elif "MD5sum" in pkgs[p["name"]]:
                                pass
                            else:
                                errors.append((p, pkgs[p["name"]]))
                        else:  # unequal version, can't decide by md5
                            errors.append((p, pkgs[p["name"]]))
                    else:  # pragma: no cover raise - defensive branch
                        errors.append((p, pkgs[p["name"]]))

                else:
                    pkgs[p["name"]] = p
            if errors:
                print("Number of duplicate, unhandled packages", len(errors))
                for p1, p2 in errors:
                    import pprint

                    print(p1["name"])
                    pprint.pprint(p1)
                    pprint.pprint(p2)
                    print("")
                raise ValueError("Duplicate packages within %s repository!"  %self.name)

            self._packages = pkgs
        return self._packages

    def parse(self, raw):
        lines = raw.split("\n")
        result = []
        current = {}
        for line in lines:
            m = re.match("([A-Za-z0-9_]+):", line)
            if m:
                key = m.groups()[0]
                value = line[line.find(":") + 2 :].strip()
                if key == "Package":
                    if current:
                        result.append(current)
                        current = {}
                if key in current:
                    raise ValueError(key)
                current[key] = value
            elif line.strip():
                current[key] += line.strip()

        if current:
            result.append(current)
        for current in result:
            for k in ["Depends", "Imports", "Suggests", "LinkingTo"]:
                if k in current:
                    current[k] = re.split(", ?", current[k].strip())
                    current[k] = set(
                        [re.findall("^[^ ()]+", x)[0] for x in current[k] if x]
                    )
                else:
                    current[k] = set()
        return result


def parse_version(v):
    try:
        return packaging.version.Version(v)
    except packaging.version.InvalidVersion:
        # handle R versions that look like 2.42-3.1
        return packaging.version.Version(v.replace("-", "."))


if __name__ == "__main__":
    install_bioconductor()
