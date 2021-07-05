==============
mbf_anysnake
==============

Welcome to **mbf_anysnake**, which 
abstracts ubuntu, python, rust, R and bioconductor versions.

It's source lives at `github <https://github.com/TyberiusPrime/mbf_anysnake>`_.

Quickstart
==========

Write this to your_project_folder/anysnake.toml

::

   [base]
   python="3.7.2"
   R="3.5.2"
   storage_path="global_anysnake_store"
   code_path="code"

   [global_python]
   jupyter=''

   [python]
   pandas=">=0.23"

Install mbf_anysnake via ``pip install mbf_anysnake``.

Get a shell inside you project via ``anysnake shell``.

This will 

- create the docker image
- install python and R
- create three virtual enviroments (one global, one local, one for the rpy2 matching the R and python version)
- install jupyter (inside the global venv)
- install pandas (inside the local venv)
- install rpy2 (inside the rpy2 venv
- start an interactive docker with a fish shell

Features
===========

- Leverage pypi and pip and allow work on selected libraries for python development
- Sane bioconductor and CRAN version managment (date based on bioconductor release date)
- 'full' install of CRAN and bioconductor 



Full configuration documentation:
==================================
Configuration is in `toml format <https://github.com/toml-lang/toml>`_ in a file
called anysnake.toml. You can create a default file by calling ``anysnake
default-config``

The following sections are supported:

[base]
------
Basic configuration.

- python="3.7.2": which python to use
- R="3.5.3": which R to use (optional)
- bioconductor="3.8": which bioconductor to use (optional, omit R if specifying
  bioconductor, it will automatically be determined to match)
- cran="full" or cran="minimal" - install all CRAN packages, or just the ones necessary
  for bioconductora
- docker_image="mbf_anysnake:18.04": optinoal, use a custom docker image 
  (not recommended, you need a ton of dependencies for CRAN packages)
- storage_path="/path": where to store python, R, the global venv, etc. Environmental
  variables are supported with ``${VARIABLE}`` syntax.
- storeage_per_hostname="true" - treat the last part of the storge_path as optional and
  go up one directory and search for other, completed builds that we could use instead.
  This applies to python, R, rpy2 and bioconductor (subject to matching whitelist and cran
  mode, see below), but not to the python global virtual env.
- code_path="path": local venv and editable libraries storage location
- global_config="/path/to/filename.toml": import lobal configuration. Local config
  directives overwrite global ones. Useful to share e.g. the storage_path and global 
  python packages between projects
- rust_versions = ["1.30.0", "nightly-2019-03-19"]: install these rust versions with
  rustup. The first one will be the 'default toolchain'. Note that the stable/nightly
  'channels' are not supported - they would be supposed to 'auto update' and anysnake only reruns the
  installation if the rust_versions definition changes.
- port = ["1234", "1234+", "1234+:4567"] - map docker ports.
  optional + means next free one
- docker_build_cmds = "RUN apt-get install -y ssh" - these are appended to the
  dockerfile when building the docker
- per_user - place to store per user files (defaults to ~/.anysnake)

[run]
------
Configuration for the run command

- additional_volumes_ro = [["/outside_docker", "/inside_docker"]]: map additional docker
  volumes, read only
- additional_volumes_rw = [["/outside_docker", "/inside_docker"]]: map additional docker
  volumes, read write
- pre_run_outside = "cmd.sh": run this before executing any run command - cwd is
  project dir, runs outside container
- pre_run_inside = "cmd.sh": run this before executing any run command, inside
  container. cwd is /project
- post_run_inside = "cmd.sh": run this after executing any run command - cwd is whatever run cmd left it at, inside continer
- post_run_outside = "cmd.sh": run this after executing any run command - cwd is project dir, outside container


[jupyter]
- pre_run_inside = "cmd.sh": run this before executing jupyter - cwd is whatever run cmd left it at, inside continer
- post_run_inside = "cmd.sh": run this after executing jupyter - cwd is whatever run cmd left it at, inside continer



[global_run]
------------
Additional volume configuration that get's merged with [run][additional_volumes_r*]

- additional_volumes_ro = [["/outside_docker", "/inside_docker"]]: map additional docker
  volumes, read only
- additional_volumes_rw = [["/outside_docker", "/inside_docker"]]: map additional docker
  volumes, read write

[build]
-------
- post_storage_build = "cmd.sh": run this if a storage build was run  - cwd is
  storge_path


[global_python]
---------------
Python packages to install into the 'global' venv (pth defined by base:storage_path),
optionally with version specification just like pip/requirements.txt.
Example ``jupyter=""`` or ``pandas=">=0.23"``.

[python]
--------
Python packages to install into the 'local' venv (pth defined by base:storage_path),
optionally with version specification just like pip/requirements.txt.
Example ``jupyter=""`` or ``pandas=">=0.23"``.

For an editable libray: ``dppd="@git+https://github.com/TyberiusPrime/dppd"``
(use "@hg+" for mercurial, use @gh/user/repo for github).

[pip_regexps]
Regeps->substitution to apply to pip-versions. This allows you to to extend 
beyond the @gh (see 'python' above) automatic.

You can either specify a replacement string (use \\1 to place captured regexps groups),
or a list, in which case simply \\1 will be replaced with the name ot the left
hand side of the = sign.

Replacements must be full specifications, including the @.


[env]
------
Additional environmental variables set inside the docker.

[bioconductor_whitelist]
------------------------
By default, bioconductor packages that need 'experimental data' or annotation packages
are not included in the install. List them in [bioconductor_whitelist] like ``chimera=""``.

Note that you will likely get more than just that package, since including it
will remove the installation block on it's prerequisites, which will in turn
possibly allow the installation of other packages that dependend on those.

You can also install every bioconductor package by specifiying ``_full_==''``


Calling other docker containers
================================
If you wish, you may export `/var/run/docker.socket` as a RW volume into
your anysnake docker. Then you can run docker containers in parallel to the
anysnake ones by using some API that can talk 'docker-socket' - e.g. 
https://pypi.org/project/docker/ .
The default ubuntu 18.04 anysnake container has the users in the appropriate
user group.


Command line interface
======================
any_snake understands the following commands:

- --help - list commands
- shell - get a shell inside the docker
- jupyter - run a jupyter server inside the docker (must have jupyter in either venv)
- run whatever - run an arbitrary command inside the docker
- rebuild - rebuild one or all all editable python packages 
- show-config - show the config as actually parsed (including global_config)
- default-config - write a default config to anysnake.toml if it is not present.
- freeze - show toml defining installed versions.

Contents
========

.. toctree::
   :maxdepth: 2


   License <license>
   Authors <authors>
   Changelog <changelog>


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

.. _toctree: http://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html
.. _reStructuredText: http://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
.. _references: http://www.sphinx-doc.org/en/stable/markup/inline.html
.. _Python domain syntax: http://sphinx-doc.org/domains.html#the-python-domain
.. _Sphinx: http://www.sphinx-doc.org/
.. _Python: http://docs.python.org/
.. _Numpy: http://docs.scipy.org/doc/numpy
.. _SciPy: http://docs.scipy.org/doc/scipy/reference/
.. _matplotlib: https://matplotlib.org/contents.html#
.. _Pandas: http://pandas.pydata.org/pandas-docs/stable
.. _Scikit-Learn: http://scikit-learn.org/stable
.. _autodoc: http://www.sphinx-doc.org/en/stable/ext/autodoc.html
.. _Google style: https://github.com/google/styleguide/blob/gh-pages/pyguide.md#38-comments-and-docstrings
.. _NumPy style: https://numpydoc.readthedocs.io/en/latest/format.html
.. _classical style: http://www.sphinx-doc.org/en/stable/domains.html#info-field-lists
