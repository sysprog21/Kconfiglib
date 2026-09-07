#!/usr/bin/env bash

# The -e is not set because we want to get all the mismatch format at once

set -u -o pipefail

set -x

REPO_ROOT="$(git rev-parse --show-toplevel)"
# Without 'set -e', an unchecked cd would leave the file lists below being
# gathered from wherever the script happened to be invoked, and the script
# would still exit 0.
cd "${REPO_ROOT}" || exit 1

# Ask git for the file list rather than walking the tree. 'find' also picked up
# vendored checkouts, build directories and __pycache__, which are not ours to
# format -- a local run against a working tree with any of those in it failed on
# files the project does not own. --others includes new files that are not yet
# committed, and --exclude-standard honours .gitignore and .git/info/exclude, so
# anything deliberately kept out of the repo stays out.
git_sources() {
	# Filtered to what is on disk: --cached still lists a tracked file that
	# has been deleted in the working tree, and shfmt and black both error
	# out on a path that is not there.
	git ls-files --cached --others --exclude-standard -- "$1" | sort -u |
		while IFS= read -r f; do [ -f "$f" ] && printf '%s\n' "$f"; done
}

SH_SOURCES=$(git_sources '*.sh')
for file in ${SH_SOURCES}; do
	shfmt -d "${file}"
done
SH_MISMATCH_FILE_CNT=0
if [ -n "${SH_SOURCES}" ]; then
	SH_MISMATCH_FILE_CNT=$(shfmt -l ${SH_SOURCES} | wc -l)
fi

PY_SOURCES=$(git_sources '*.py')
for file in ${PY_SOURCES}; do
	echo "Checking Python file: ${file}"
	black --diff "${file}"
done
PY_MISMATCH_FILE_CNT=0
if [ -n "${PY_SOURCES}" ]; then
	PY_MISMATCH_FILE_CNT=$(echo "$(black --check ${PY_SOURCES} 2>&1)" | grep -c "^would reformat ")
fi

exit $((SH_MISMATCH_FILE_CNT + PY_MISMATCH_FILE_CNT))
