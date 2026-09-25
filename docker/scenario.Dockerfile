# syntax=docker/dockerfile:1
# Per-scenario sandbox image (doc 07 §2, build phase). Build context: the scenario directory.
#   uv run aeropatch build <scenario_id>
# Tests are baked in from the pristine scenario, so a patch can never change the tests it is judged by.
ARG BASE=aeropatch-sandbox-base:latest
FROM ${BASE}

USER root
COPY requirements.lock /opt/scenario/requirements.lock
RUN --mount=type=secret,id=ca,required=false \
    if [ -f /run/secrets/ca ]; then export PIP_CERT=/run/secrets/ca; fi; \
    if grep -qvE '^[[:space:]]*(#|$)' /opt/scenario/requirements.lock; then \
        pip install --require-hashes -r /opt/scenario/requirements.lock; \
    fi

COPY repo /opt/scenario/repo
COPY tests_poc /opt/scenario/tests_poc
COPY tests_regression /opt/scenario/tests_regression
RUN chmod -R a-w /opt/scenario

USER 10001:10001
WORKDIR /work
CMD ["/harness/run.sh"]
