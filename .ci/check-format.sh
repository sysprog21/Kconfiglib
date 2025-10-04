#!/usr/bin/env bash

# The -e is not set because we want to get all the mismatch format at once

set -u -o pipefail

set -x

REPO_ROOT="$(git rev-parse --show-toplevel)"

SH_SOURCES=$(find "${REPO_ROOT}" | egrep "\.sh$")
for file in ${SH_SOURCES}; do
	shfmt -d "${file}"
done
SH_MISMATCH_FILE_CNT=0
if [ -n "${SH_SOURCES}" ]; then
	SH_MISMATCH_FILE_CNT=$(shfmt -l ${SH_SOURCES} | wc -l)
fi

PY_SOURCES=$(find "${REPO_ROOT}" | egrep "\.py$")
for file in ${PY_SOURCES}; do
	echo "Checking Python file: ${file}"
	black --diff "${file}"
done
PY_MISMATCH_FILE_CNT=0
if [ -n "${PY_SOURCES}" ]; then
	PY_MISMATCH_FILE_CNT=$(echo "$(black --check ${PY_SOURCES} 2>&1)" | grep -c "^would reformat ")
fi

exit $((SH_MISMATCH_FILE_CNT + PY_MISMATCH_FILE_CNT))
