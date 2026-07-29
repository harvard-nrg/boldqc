FROM rockylinux:8

# install useful (but not entirely necessary) things
RUN dnf install -y git vim

# install some needed things
RUN dnf install -y python3 python3-devel

# set python to python3
RUN alternatives --set python /usr/bin/python3

# install pipenv
RUN pip3 install pipenv==2021.5.29

# install fsl
ARG FSL_PREFIX="/sw/apps/fsl/"
ARG FSL_URI="https://www.dropbox.com/s/p8go1t8kcoe41pz/fsl-6.0.4-centos7_64.tar.gz?dl=0"
RUN dnf install -y libquadmath
RUN mkdir -p "${FSL_PREFIX}"
RUN curl -L -s "${FSL_URI}" | tar -C "${FSL_PREFIX}" -xzf - \
  --strip-components=1

# install boldqc
ARG BQC_PREFIX="/sw/apps/boldqc"
ARG BQC_VERSION="0.7.1"
RUN dnf install -y compat-openssl10 redhat-lsb-core
RUN mkdir -p "${BQC_PREFIX}"
ENV PIPENV_VENV_IN_PROJECT=1
WORKDIR "${BQC_PREFIX}"
RUN pipenv install boldqc=="${BQC_VERSION}"
ENV PIPENV_PIPFILE="${BQC_PREFIX}/Pipfile"

# install dcm2niix
ARG DN2_PREFIX="/sw/apps/dcm2niix"
ARG DN2_VERSION="v1.0.20260724"
ARG DN2_URI="https://github.com/rordenlab/dcm2niix"
WORKDIR "${DN2_PREFIX}"
RUN dnf install -y gcc-c++
RUN git clone -b "${DN2_VERSION}" --single-branch "${DN2_URI}" . && \
  cd "console" && \
  make

# fsl environment
ENV FSLDIR="${FSL_PREFIX}"
ENV FSLGECUDAQ="cuda.q" \
    FSLMULTIFILEQUIT="TRUE" \
    FSLOUTPUTTYPE="NIFTI_GZ" \
    FSLWISH="${FSLDIR}/bin/fslwish" \
    FSLTCLSH="${FSLDIR}/bin/fsltclsh" \
    FSLMACHINELIST="" \
    FSLREMOTECALL="" \
    FSLLOCKDIR=""
ENV PATH="${FSLDIR}/bin:${PATH}"

# dcm2niix environment
ENV PATH="${DN2_PREFIX}/console:${PATH}"

# configure entrypoint
WORKDIR /sw/apps/boldqc
ENTRYPOINT ["pipenv", "run", "boldQC.py"]

