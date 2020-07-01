FROM ubuntu:18.04 
RUN sed -Ei 's/^# deb-src /deb-src /' /etc/apt/sources.list
RUN apt-get update
ENV DEBIAN_FRONTEND noninteractive

RUN addgroup --gid 2000 g2000

RUN useradd --uid 1000 --gid 2000 --home=/home/u1000 --create-home -p "$1$gvr9drEv$OT4HrhzzvU5HzBZ4yA.LR1"--shell=/bin/bash u1000
RUN useradd --uid 1001 --gid 2000 --home=/home/u1001 --create-home -p "$1$gvr9drEv$OT4HrhzzvU5HzBZ4yA.LR1"--shell=/bin/bash u1001
RUN useradd --uid 1002 --gid 2000 --home=/home/u1002 --create-home -p "$1$gvr9drEv$OT4HrhzzvU5HzBZ4yA.LR1"--shell=/bin/bash u1002
RUN useradd --uid 1003 --gid 2000 --home=/home/u1003 --create-home -p "$1$gvr9drEv$OT4HrhzzvU5HzBZ4yA.LR1"--shell=/bin/bash u1003
RUN useradd --uid 1004 --gid 2000 --home=/home/u1004 --create-home -p "$1$gvr9drEv$OT4HrhzzvU5HzBZ4yA.LR1" --shell=/bin/bash u1004
RUN echo "root:test123" | chpasswd

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

RUN echo "u1000:test123" | chpasswd
RUN echo "u1001:test123" | chpasswd
RUN echo "u1002:test123" | chpasswd
RUN echo "u1003:test123" | chpasswd
RUN echo "u1004:test123" | chpasswd
RUN usermod -g sudo u1000
RUN usermod -g sudo u1001
RUN usermod -g sudo u1002
RUN usermod -g sudo u1003
RUN usermod -g sudo u1004
RUN mkdir /home/u1000/.config /home/u1001/.config /home/u1002/.config /home/u1003/.config /home/u1004/.config
RUN chown u1000 /home/u1000 -R
RUN chown u1001 /home/u1001 -R
RUN chown u1002 /home/u1002 -R
RUN chown u1003 /home/u1003 -R
RUN chown u1004 /home/u1004 -R
#RUN apt-get install -y 
COPY sudoers /etc/sudoers
RUN chmod 440 /etc/sudoers
RUN apt-get -y install ssh && mkdir /run/sshd
