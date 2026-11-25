ARG PULSE_LOADER_RESOLUTION_BASE=docker.io/library/python@sha256:174bec68e0451bffabbb08c7d5d21c6b253f772d81d52b9558af97bb3159b761
FROM ${PULSE_LOADER_RESOLUTION_BASE}

# The controller permits only its private local tag for this exact base config.
# Both jobs preserve/reload the selected base and build with --network=none.
COPY environment.json requirements.lock build_environment.py /opt/pulse-loader-resolution-build/
COPY debs/ /opt/pulse-loader-resolution-build/debs/
COPY wheels/ /opt/pulse-loader-resolution-build/wheels/
COPY native/ /opt/pulse-loader-resolution-build/native/
RUN ["/usr/local/bin/python3.11", "-I", "-B", "/opt/pulse-loader-resolution-build/build_environment.py", "--inputs", "/opt/pulse-loader-resolution-build"]

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 LC_ALL=C TZ=UTC
WORKDIR /repo
