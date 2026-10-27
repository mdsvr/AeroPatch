# syntax=docker/dockerfile:1
# Folder sandbox image (doc 17 part 4 §2). Build context: runs/folders/<id>/context, a staged copy
# of the user's folder, never the folder itself. Dependencies first, so an edit to the code
# rebuilds only the last layers. The build is the only step with network.
ARG BASE=aeropatch-sandbox-base:latest
FROM ${BASE}

USER root
ARG APT=""
RUN if [ -n "$APT" ]; then apt-get update && apt-get install -y --no-install-recommends $APT \
        && rm -rf /var/lib/apt/lists/*; fi
COPY deps/ /opt/deps/
RUN --mount=type=secret,id=ca,required=false \
    if [ -f /run/secrets/ca ]; then export PIP_CERT=/run/secrets/ca; fi; \
    for f in /opt/deps/*.txt; do [ -f "$f" ] && pip install -r "$f" || exit 1; done; true

COPY repo /opt/scenario/repo
ARG EDITABLE=""
RUN --mount=type=secret,id=ca,required=false \
    if [ -n "$EDITABLE" ]; then cd /tmp && cp -r /opt/scenario/repo /tmp/build && \
        (pip install "/tmp/build[test]" || pip install /tmp/build) && rm -rf /tmp/build; fi
COPY extra/ /opt/scenario/
COPY folder_run.sh folder_runner.py /opt/folder/
RUN chmod -R a-w /opt/scenario && chmod 555 /opt/folder/folder_run.sh /opt/folder/folder_runner.py

USER 10001:10001
WORKDIR /work
CMD ["/opt/folder/folder_run.sh"]
