FROM ubuntu:eoan as build

ENV LANG C.UTF-8

RUN apt-get update && \
    apt-get install --no-install-recommends --yes \
        python3 python3-dev python3-setuptools python3-pip python3-venv \
        build-essential portaudio19-dev

ENV APP_DIR=/usr/lib/rhasspy-lisa-odas-hermes
ENV BUILD_DIR=/build

# Copy source
COPY rhasspy_lisa_odas_hermes/ ${BUILD_DIR}/rhasspy_lisa_odas_hermes/

# Autoconf
COPY m4/ ${BUILD_DIR}/m4/
COPY configure config.sub config.guess \
     install-sh missing aclocal.m4 \
     Makefile.in setup.py requirements.txt rhasspy-lisa-odas-hermes.in \
     ${BUILD_DIR}/

RUN cd ${BUILD_DIR} && \
    ./configure --prefix=${APP_DIR}

COPY VERSION README.md LICENSE ${BUILD_DIR}/

RUN cd ${BUILD_DIR} && \
    make && \
    make install

# Strip binaries and shared libraries
RUN (find ${APP_DIR} -type f \( -name '*.so*' -or -executable \) -print0 | xargs -0 strip --strip-unneeded -- 2>/dev/null) || true

# -----------------------------------------------------------------------------

FROM ubuntu:eoan as run

ENV LANG C.UTF-8

RUN apt-get update && \
    apt-get install --yes --no-install-recommends \
        python3 libpython3.7 \
        libportaudio2

ENV APP_DIR=/usr/lib/rhasspy-lisa-odas-hermes
COPY --from=build ${APP_DIR}/ ${APP_DIR}/
COPY --from=build /build/rhasspy-lisa-odas-hermes /usr/bin/

ENTRYPOINT ["bash", "/usr/bin/rhasspy-lisa-odas-hermes"]
