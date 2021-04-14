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
RUN useradd --uid 1018 --gid 2000 --home=/home/u1018 --create-home -p "$1$gvr9drEv$OT4HrhzzvU5HzBZ4yA.LR1" --shell=/bin/bash u1018
RUN echo "root:test123" | chpasswd

RUN apt-get update && apt-get install -y \
  adduser\
  apt\
  autoconf\
  automake autopoint bash-completion bison \
  base-files\
  base-passwd\
  bash\
  blt-dev\
  bsdmainutils\
  bsdutils\
  build-essential\
  bwidget \
  bzip2\
  ca-certificates\
  clang-6.0\
  cmake\
  coinor-libclp-dev\
  coinor-libsymphony-dev\
  coreutils\
  cpanminus\
  curl\
  dash\
  debconf\
  debhelper \
  debianutils\
  default-jdk\
  default-jdk-headless\
  default-jre\
  default-jre-headless\
  default-libmysqlclient-dev\
  dh-autoreconf\
  dh-strip-nondeterminism\
  diffutils\
  docutils-common\
  dpkg\
  e2fsprogs\
  fdisk\
  findutils\
  fish \
  fonts-lmodern\
  freeglut3-dev \
  gettext\
  gettext-base\
  gfortran\
  ggobi\
  gir1.2-freedesktop\
  gir1.2-pango-1.0\
  git\
  gnuplot\
  gpgv\
  grep\
  groff-base\
  gsl-bin \
  gtk2.0 \
  gzip\
  hostname\
  imagemagick \
  init-system-helpers\
  intltool-debian\
  jags \
  jags\
  libacl1\
  libapparmor-dev\
  libapt-pkg5.0\
  libarchive-zip-perl\
  libasan5\
  libattr1\
  libaudit1\
  libaudit-common\
  libavfilter-dev\
  libbison-dev\
  libblas3\
  libblas-dev\
  libblkid1\
  libbz2-1.0\
  libbz2-dev \
  libc6\
  libcairo2-dev\
  libcairo-script-interpreter2\
  libcap-ng0\
  libc-bin\
  libcgal-dev \
  libclang1\
  libclang-dev\
  libcom-err2\
  libcupsimage2\
  libcurl4-gnutls-dev \
  libdb5.3\
  libdb5.3-dev\
  libdb-dev\
  libdebconfclient0\
  libdieharder-dev\
  libext2fs2\
  libfdisk1\
  libffi6\
  libfftw3-dev \
  libfile-stripnondeterminism-perl\
  libgcrypt20\
  libgdal-dev\
  libgdbm-dev\
  libgeos-dev\
  libglpk-dev\
  libglu1-mesa-dev \
  libgmp10\
  libgmp10\
  libgnutls30\
  libgpg-error0\
  libgpgme11-dev\
  libgraphicsmagick1-dev \
  libgs9\
  libgs9-common\
  libgsl0-dev \
  libgsl23 \
  libgtk2.0-dev \
  libgtkmm-2.4-dev \
  libhiredis-dev\
  libhogweed4\
  libhts-dev \
  libidn11\
  libidn2-0\
  libijs-0.35\
  libjbig2dec0\
  libjbig-dev\
  libjpeg8-dev\
  libjpeg-dev\
  libjpeg-turbo8-dev\
  libjq-dev\
  libkpathsea6\
  liblapack3\
  liblapack-dev\
  libleptonica-dev\
  liblz4-1\
  liblzma5\
  liblzma-dev \
  liblzo2-2\
  liblzo2-dev\
  libmagic-dev\
  libmagick++-dev \
  libmariadbclient18 \
  libmecab-dev\
  libmecab-dev\
  libmime-charset-perl\
  libmount1\
  libmpdec-dev\
  libmpfr-dev \
  libmysqlclient-dev\
  libncurses5\
  libncurses5-dev \
  libncursesw5\
  libncursesw5-dev\
  libnetcdf-dev \
  libnettle6\
  libopenbabel-dev \
  libopenblas-base \
  libopenblas-dev \
  libopenmpi-dev \
  libp11-kit0\
  libpam0g\
  libpam-modules\
  libpam-modules-bin\
  libpam-runtime\
  libpango1.0-dev\
  libpangoxft-1.0-0\
  libpaper1\
  libpaper-utils\
  libpcre2-dev \
  libpcre2-posix0 \
  libpcre3\
  libpixman-1-dev\
  libpoppler73\
  libpoppler-cpp-dev\
  libpoppler-dev\
  libpoppler-glib-dev\
  libpotrace0\
  libpq-dev\
  libprocps6\
  libproj-dev\
  libprotobuf-dev\
  libprotoc-dev\
  libpython2.7-minimal\
  libpython2.7-stdlib\
  libpython-stdlib\
  libquantlib0-dev\
  libraptor2-dev \
  librasqal3-dev \
  librdf0-dev\
  libreadline-dev \
  librrd-dev\
  libsasl2-dev \
  libsbml5-dev \
  libsbml5-dev\
  libseccomp2\
  libselinux1\
  libsemanage1\
  libsemanage-common\
  libsepol1\
  libsigsegv2\
  libsmartcols1\
  libsndfile1\
  libsndfile1-dev\
  libsodium23 \
  libsodium-dev\
  libsombok3\
  libsqlite3-dev \
  libss2\
  libssh-dev\
  libssl1.0.0\
  libssl1.1\
  libssl-dev \
  libssl-dev\
  libstdc++6\
  libsystemd0\
  libtasn1-6\
  libtbb2\
  libtbb-dev\
  libtesseract-dev\
  libtext-unidecode-perl\
  libtiff5-dev\
  libtiffxx5\
  libtimedate-perl\
  libtinfo5\
  libubsan1\
  libudev1\
  libudunits2-0 \
  libudunits2-dev \
  libunicode-linebreak-perl\
  libunistring2\
  libuuid1\
  libv8-3.14-dev\
  libxcb-render0-dev\
  libxcb-shm0-dev\
  libxfont2\
  libxkbfile1\
  libxml2-dev \
  libxml-libxml-perl\
  libxml-namespacesupport-perl\
  libxml-sax-base-perl\
  libxml-sax-perl\
  libxmlsec1-dev \
  libz-dev\
  libzmq3-dev\
  libzstd1\
  libzzip-0-13\
  llvm\
  login\
  lsb-base\
  m4\
  make\
  man-db\
  mawk\
  mercurial\
  mesa-common-dev \
  mount\
  mpack\
  ncurses-base\
  ncurses-bin\
  nvidia-cuda-dev\
  nvidia-cuda-toolkit\
  nvidia-opencl-dev\
  opencl-headers\
  openjdk-11-jdk\
  openjdk-11-jdk-headless\
  openjdk-11-jre\
  openjdk-11-jre-headless\
  openjdk-8-jdk\
  openjdk-8-jre\
  passwd\
  perl-base\
  po-debconf\
  poppler-data\
  procps\
  protobuf-compiler\
  python\
  python2.7\
  python2.7-minimal\
  python3-dev \
  python-dev\
  python-minimal\
  python-openssl\
  quilt\
  rsync\
  sed\
  sensible-utils\
  sudo\
  sysvinit-utils\
  t1utils\
  tar\
  tcl8.6-dev \
  tesseract-ocr-eng\
  tk-dev \
  tzdata\
  ubuntu-keyring\
  unixodbc-dev\
  unzip\
  util-linux\
  vim\
  wget\
  x11-xkb-utils\
  xdg-utils\
  xfonts-base\
  xfonts-encodings\
  xfonts-utils\
  xserver-common\
  xvfb\
  xz-utils\
  zlib1g\
  zlib1g-dev 
RUN ln -s  /usr/bin/nvcc /bin/nvcc
RUN mkdir -p /usr/local/cuda/bin
RUN ln -s  /usr/bin/nvcc  /usr/local/cuda/bin/nvcc
RUN echo "u1000:test123" | chpasswd
RUN echo "u1001:test123" | chpasswd
RUN echo "u1002:test123" | chpasswd
RUN echo "u1003:test123" | chpasswd
RUN echo "u1004:test123" | chpasswd
RUN echo "u1018:test123" | chpasswd
RUN usermod -g sudo u1000
RUN usermod -g sudo u1001
RUN usermod -g sudo u1002
RUN usermod -g sudo u1003
RUN usermod -g sudo u1004
RUN usermod -g sudo u1018
RUN mkdir /home/u1000/.config /home/u1001/.config /home/u1002/.config /home/u1003/.config /home/u1004/.config /home/u1018/.config
RUN chown u1000 /home/u1000 -R
RUN chown u1001 /home/u1001 -R
RUN chown u1002 /home/u1002 -R
RUN chown u1003 /home/u1003 -R
RUN chown u1004 /home/u1004 -R
RUN chown u1018 /home/u1018 -R
RUN apt-get update
RUN apt-get install -y libgit2-dev libopencv-dev python3-dev pandoc pandoc-citeproc ghostscript
COPY sudoers /etc/sudoers
RUN chmod 440 /etc/sudoers
RUN apt-get update
RUN apt-get -y install ssh samtools && mkdir /run/sshd
RUN apt-get -y install libfribidi-dev libharfbuzz-dev
RUN groupadd -g 999 docker && usermod -a -G docker u1000 && usermod -a -G docker u1001 && usermod -a -G docker u1002 && usermod -a -G docker u1003 && usermod -a -G docker u1004 && usermod -a -G docker u1018
