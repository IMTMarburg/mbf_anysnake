FROM ubuntu:18.04 
RUN sed -Ei 's/^# deb-src /deb-src /' /etc/apt/sources.list
RUN apt-get update
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get install -y \
  adduser\
  apt\
  autoconf\
  automake \
  autopoint \
  base-files\
  base-passwd\
  bash\
  build-essential\
  bzip2\
  ca-certificates\
  clang-6.0\
  cmake\
  coreutils\
  curl\
  debconf\
  debhelper \
  debianutils\
  dpkg\
  fish \
  fonts-lmodern\
  freeglut3-dev \
  gettext\
  gettext-base\
  gfortran\
  git\
  gzip\
  hostname\
  libc6\
  libbz2-dev \
  libsqlite3-dev\
  libssl1.0.0\
  libssl1.1\
  libssl-dev\
  make\
  mercurial\
  python\
  python2.7\
  python2.7-minimal\
  python3-dev \
  python-dev\
  python-minimal\
  python-openssl\
  sudo\
  tar\
  tzdata\
  vim\
  wget\
  zlib1g\
  zlib1g-dev 

RUN apt-get -y install ssh && mkdir /run/sshd
