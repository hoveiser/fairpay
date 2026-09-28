#!/usr/bin/env bash
# Seed genlayer-test's Direct-mode runner cache from genvm-lint's bundle.
#
# Root cause (verified on a clean runner):
#   gltest's direct runner (gltest/direct/sdk_loader.py) downloads the
#   UNVERSIONED GitHub release asset "genvm-universal.tar.xz" for the latest
#   genvm release (currently v0.3.0-rc7). Recent genvm releases renamed that
#   bundle to "genvm-runners-all.tar.xz", so the runner's request returns HTTP
#   404. On a developer machine the tests still pass only because the bundle is
#   already sitting in ~/.cache/gltest-direct from an earlier run.
#
# genvm-lint already resolves the correct asset (it tries genvm-runners-all
# first, then the old name) and caches it under the versioned filename that
# gltest looks for, and that bundle contains the runner hash this contract
# pins. So we let genvm-lint fetch it and copy it into gltest's cache.
#
# This does not skip, xfail, weaken or mock any test; it only provides the
# binary artifact the pinned runner needs, the same one genvm-lint uses.
set -euo pipefail

CONTRACT="${1:-contracts/contract.py}"
LINTER_CACHE="${GENLAYER_LINTER_CACHE:-$HOME/.cache/genvm-linter}"
GLTEST_CACHE="${GENLAYER_GLTEST_CACHE:-$HOME/.cache/gltest-direct}"

# 1. Make sure genvm-lint has downloaded a bundle for this contract's runner.
if ! ls "$LINTER_CACHE"/genvm-universal-*.tar.xz >/dev/null 2>&1; then
  echo "No genvm bundle in $LINTER_CACHE; fetching via genvm-lint for $CONTRACT"
  genvm-lint check "$CONTRACT" >/dev/null
fi

# 2. Seed the gltest Direct-mode cache from the newest available bundle.
latest_bundle="$(ls -1 "$LINTER_CACHE"/genvm-universal-*.tar.xz | sort -V | tail -1)"
mkdir -p "$GLTEST_CACHE"
name="$(basename "$latest_bundle")"
if [ -e "$GLTEST_CACHE/$name" ]; then
  echo "Already seeded: $GLTEST_CACHE/$name"
else
  ln "$latest_bundle" "$GLTEST_CACHE/$name" 2>/dev/null || cp "$latest_bundle" "$GLTEST_CACHE/$name"
  echo "Seeded $GLTEST_CACHE/$name"
fi
