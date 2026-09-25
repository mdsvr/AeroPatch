#!/bin/sh
# Runs inside the sandbox (doc 07 §6). Network is off and the root filesystem is read-only.
# Input (read-only mount /src):
#   /src/repo/         scratch copy of the scenario repo with the candidate patch already applied
#   /src/changed.txt   repo-relative paths the patch touched (may be empty)
# Output: sections on stdout between ===AEROPATCH-<NAME>=== markers, parsed by sandbox.py.
set -u
export PYTHONPATH=/work/repo HOME=/tmp
MAX=400000

cp -r /src/repo /work/repo
chmod -R u+w /work/repo
# Tests come from the image, never from the patched tree.
cp -r /opt/scenario/tests_poc /work/tests_poc
cp -r /opt/scenario/tests_regression /work/tests_regression

for suite in poc regression; do
    timeout 240 python -m pytest -q -p no:cacheprovider --timeout=30 \
        --rootdir=/work --junitxml=/tmp/$suite.xml /work/tests_$suite >/tmp/$suite.log 2>&1
    rc=$?
    echo "===AEROPATCH-RC-$suite==="
    echo "$rc"
    echo "===AEROPATCH-JUNIT-$suite==="
    head -c $MAX /tmp/$suite.xml 2>/dev/null
    echo
    echo "===AEROPATCH-LOG-$suite==="
    tail -c 20000 /tmp/$suite.log
done

cd /work/repo
changed=$(grep '\.py$' /src/changed.txt 2>/dev/null | tr '\n' ' ')
if [ -n "$changed" ]; then
    echo "===AEROPATCH-RUFF==="
    # shellcheck disable=SC2086
    ruff check --no-cache --output-format json $changed 2>/dev/null | head -c $MAX
    echo
    echo "===AEROPATCH-BANDIT==="
    # shellcheck disable=SC2086
    bandit -q -f json $changed 2>/dev/null | head -c $MAX
    echo
fi
echo "===AEROPATCH-END==="
