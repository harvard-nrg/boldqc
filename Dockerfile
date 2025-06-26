FROM rockylinux:8

# install useful (but not entirely necessary) things
RUN dnf install -y git vim

# install some things
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

# install dcm2niix
ARG D2N_PREFIX="/sw/apps/dcm2niix"
ARG D2N_URI="https://github.com/rordenlab/dcm2niix/releases/download/v1.0.20230411/dcm2niix_lnx.zip"
RUN dnf install -y unzip
RUN mkdir -p "${D2N_PREFIX}"
RUN curl -sL "${D2N_URI}" -o "/tmp/dcm2niix_lnx.zip"
WORKDIR "${D2N_PREFIX}"
RUN unzip "/tmp/dcm2niix_lnx.zip"
RUN rm "/tmp/dcm2niix_lnx.zip"

# install boldqc
ARG BQC_PREFIX="/sw/apps/boldqc"
ARG BQC_VERSION="0.5.0"
RUN dnf install -y compat-openssl10 redhat-lsb-core
RUN mkdir -p "${BQC_PREFIX}"
ENV PIPENV_VENV_IN_PROJECT=1
WORKDIR "${BQC_PREFIX}"
RUN pipenv install boldqc=="${BQC_VERSION}"
ENV PIPENV_PIPFILE="${BQC_PREFIX}/Pipfile"

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
ENV PATH="${D2N_PREFIX}:${PATH}"

# configure entrypoint
WORKDIR /sw/apps/boldqc
ENTRYPOINT ["pipenv", "run", "boldQC.py"]

