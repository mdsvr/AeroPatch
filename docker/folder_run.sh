#!/bin/sh
# Folder mode of the sandbox (doc 17 part 4 §3). Same input and output contract as run.sh:
#   /src/repo/ the scratch copy with the candidate change, /src/changed.txt the touched paths.
# The pristine tests and test settings are copied back over the candidate, so the tests that run
# are the user's own. A PoC suite runs only when the image has one (/opt/scenario/tests_poc).
set -u
export HOME=/tmp
MAX=400000

cp -r /src/repo /work/repo
chmod -R u+w /work/repo
cd /opt/scenario/repo
find . \( -path './tests/*' -o -name 'test_*.py' -o -name '*_test.py' -o -name conftest.py -o -name pyproject.toml \
    -o -name setup.cfg -o -name pytest.ini -o -name tox.ini \) -type f | while read -r f; do
    mkdir -p "/work/repo/$(dirname "$f")"
    cp "$f" "/work/repo/$f"
done
chmod -R u+w /work/repo
cd /work/repo

if [ -f /opt/scenario/pass_set.txt ]; then export AEROPATCH_PASS_SET=/opt/scenario/pass_set.txt; fi
timeout 240 python -I /opt/folder/folder_runner.py -q -p no:cacheprovider --timeout=30 \
    --junitxml=/tmp/regression.xml >/tmp/regression.log 2>&1
rc=$?
echo "===AEROPATCH-RC-regression==="
echo "$rc"
echo "===AEROPATCH-JUNIT-regression==="
head -c $MAX /tmp/regression.xml 2>/dev/null
echo
echo "===AEROPATCH-LOG-regression==="
tail -c 20000 /tmp/regression.log
echo "===AEROPATCH-OUTCOMES==="
head -c $MAX /tmp/outcomes.txt 2>/dev/null
echo

if [ -d /opt/scenario/tests_poc ]; then
    unset AEROPATCH_PASS_SET
    timeout 240 python -I /opt/folder/folder_runner.py -q -p no:cacheprovider --timeout=30 -c /dev/null \
        --rootdir=/work --junitxml=/tmp/poc.xml /opt/scenario/tests_poc >/tmp/poc.log 2>&1
    rc=$?
    echo "===AEROPATCH-RC-poc==="
    echo "$rc"
    echo "===AEROPATCH-JUNIT-poc==="
    head -c $MAX /tmp/poc.xml 2>/dev/null
    echo
    echo "===AEROPATCH-LOG-poc==="
    tail -c 20000 /tmp/poc.log
fi

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
