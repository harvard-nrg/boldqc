FROM rockylinux:8

# upgrade certificates
RUN dnf upgrade -y ca-certificates

# install useful (but not entirely necessary) things
RUN dnf install -y git vim

# install some needed things
RUN dnf install -y python3.12

# set python to python3
RUN alternatives --set python /usr/bin/python3.12
RUN python3 -m ensurepip --default-pip

# install pipenv
RUN pip install "certifi>=2026.10.19" "pip>=26.2.2"

# install fsl
ARG FSL_PREFIX="/sw/apps/fsl/"
ARG FSL_URI="https://www.dropbox.com/scl/fi/3q2292enpxh5guy0rywsu/fsl-6.0.4-centos7_64.tar.gz?rlkey=eahcgw5uw3zdqyv8nns9gpkpn&st=g7haorvl&dl=1"
RUN dnf install -y libquadmath
RUN mkdir -p "${FSL_PREFIX}"
RUN curl -L -s "${FSL_URI}" | tar -C "${FSL_PREFIX}" -xzf - \
  --strip-components=1

# install boldqc
ARG BQC_PREFIX="/sw/apps/boldqc"
RUN dnf install -y compat-openssl10 redhat-lsb-core
RUN mkdir -p "${BQC_PREFIX}"
COPY . "${BQC_PREFIX}"
WORKDIR "${BQC_PREFIX}"
RUN python3 -m venv .venv
RUN .venv/bin/pip install .

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

# boldqc environment
ENV PATH="${BQC_PREFIX}/.venv/bin:${PATH}"

# configure entrypoint
ENTRYPOINT ["boldQC.py"]

