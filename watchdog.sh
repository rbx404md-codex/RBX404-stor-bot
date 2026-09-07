#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"
delay="${RESTART_DELAY_SECONDS:-5}"

while true; do
  printf '[watchdog] %s starting RBX404 bot\n' "$(date -Is)"
  python main.py || status=$?
  status="${status:-0}"
  printf '[watchdog] %s exited with status %s; retrying in %ss\n' "$(date -Is)" "$status" "$delay"
  sleep "$delay"
  unset status
done