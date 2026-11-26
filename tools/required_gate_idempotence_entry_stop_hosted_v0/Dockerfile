ARG PULSE_ENTRY_STOP_BASE=docker.io/library/python@sha256:174bec68e0451bffabbb08c7d5d21c6b253f772d81d52b9558af97bb3159b761
FROM ${PULSE_ENTRY_STOP_BASE}

# The fixed caller may supply its private local tag after checking its exact
# pinned config ID. The tag is preserved with docker save/load across jobs;
# it is not a workflow input or an independently selectable base image.

# Build with --platform=linux/amd64 --network=none. The caller prepares a
# bounded context containing only these reviewed files and verified downloads.
# This selects build inputs; it does not assert byte-identical image builds.
COPY environment.json requirements.lock build_environment.py /opt/pulse-entry-stop-build/
COPY debs/ /opt/pulse-entry-stop-build/debs/
COPY wheels/ /opt/pulse-entry-stop-build/wheels/
COPY native/ /opt/pulse-entry-stop-build/native/

RUN ["/usr/local/bin/python3.11", "-I", "/opt/pulse-entry-stop-build/build_environment.py", "--inputs", "/opt/pulse-entry-stop-build"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONNOUSERSITE=1 \
    PIP_NO_INDEX=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# The acquisition caller supplies its numeric UID:GID, read-only mounts, an
# isolated output mount, network=none and the selected resource restrictions.
# The inherited Docker seccomp and AppArmor policies are retained unchanged.
WORKDIR /repo
