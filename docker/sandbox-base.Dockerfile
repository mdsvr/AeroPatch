# syntax=docker/dockerfile:1
# AeroPatch sandbox base image (doc 07 §3). Build context: repository root.
#   uv run aeropatch build-base
# The base is pinned by digest so benchmark runs are reproducible.
FROM python:3.12-slim@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# No git or compilers in the image: patches are applied host-side into a throwaway
# scratch copy, which is mounted read-only at /src (doc 07 §5).

# Harness tools, hash-pinned. An optional build secret `ca` supplies a proxy CA bundle.
COPY docker/harness-requirements.lock /tmp/harness.lock
RUN --mount=type=secret,id=ca,required=false \
    if [ -f /run/secrets/ca ]; then export PIP_CERT=/run/secrets/ca; fi; \
    pip install --require-hashes -r /tmp/harness.lock && rm /tmp/harness.lock

RUN useradd --uid 10001 --no-create-home --home-dir /tmp sandbox
COPY docker/run.sh /harness/run.sh
RUN chmod 555 /harness/run.sh

USER 10001:10001
WORKDIR /work
