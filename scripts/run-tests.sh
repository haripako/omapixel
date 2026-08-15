#!/usr/bin/env bash
#
# Run the test suite.
#
#   scripts/run-tests.sh              everything
#   scripts/run-tests.sh --watch      re-run whenever a tracked file changes
#   scripts/run-tests.sh -q           quiet
#   scripts/run-tests.sh tests.test_build_matrix     one module
#
# Standard library only: no pytest, no network, no package to install. The
# suite never starts a binary that talks to hardware — see tests/README.md for
# why that is a hard rule on this machine rather than a preference.
#
# LC_ALL=C is not decoration. Localised output has already cost this project a
# wrong percentile calculation through a decimal comma.
#
set -uo pipefail

cd "$(dirname "$0")/.."
export LC_ALL=C

# --watch: poll for changes and re-run. Polling rather than inotify because
# inotify-tools is not installed on the reference machine and this script must
# not require installing anything. Four agents write to this tree at once, so
# the fingerprint covers everything the suite reads, not just tests/.
if [ "${1:-}" = "--watch" ]; then
  shift
  fingerprint() {
    find tests scripts data docs -type f \
         \( -name '*.py' -o -name '*.sh' -o -name '*.toml' -o -name '*.md' \) \
         -newermt '1970-01-02' -printf '%p %T@\n' 2>/dev/null | sort
  }
  echo "watching tests/ scripts/ data/ docs/ — ctrl-c to stop"
  previous=
  while true; do
    current=$(fingerprint)
    if [ "$current" != "$previous" ]; then
      [ -n "$previous" ] && echo && echo "== change detected, $(date '+%H:%M:%S') =="
      "$0" "$@"
      previous=$current
    fi
    sleep 2
  done
fi

status=0

echo "== unit tests =="
if [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; then
  python3 -m unittest "$@" || status=1
else
  python3 -m unittest discover -t . -s tests "$@" || status=1
fi

echo
echo "== shell syntax =="
for script in scripts/*.sh; do
  if bash -n "$script"; then
    echo "  ok  $script"
  else
    echo "  FAIL $script"
    status=1
  fi
done

echo
echo "== shellcheck =="
if command -v shellcheck &>/dev/null; then
  shellcheck --severity=warning scripts/*.sh || status=1
else
  # Not installed on the reference machine. CI runs it; locally it degrades to
  # a notice rather than a failure nobody can reproduce.
  echo "  skipped: shellcheck is not installed (CI runs it)"
fi

echo
if [ "$status" -eq 0 ]; then
  echo "all green"
else
  echo "FAILURES — see above" >&2
fi
exit "$status"
