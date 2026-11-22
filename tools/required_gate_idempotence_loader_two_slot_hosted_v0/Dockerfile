ARG PULSE_TWO_SLOT_BASE=docker.io/library/python@sha256:174bec68e0451bffabbb08c7d5d21c6b253f772d81d52b9558af97bb3159b761
FROM ${PULSE_TWO_SLOT_BASE}

COPY environment.json requirements.lock build_environment.py /opt/pulse-two-slot-build/
COPY wheels/ /opt/pulse-two-slot-build/wheels/
RUN ["/usr/local/bin/python3.11", "-I", "-B", "/opt/pulse-two-slot-build/build_environment.py", "--inputs", "/opt/pulse-two-slot-build"]

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /repo
