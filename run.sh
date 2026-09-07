#!/usr/bin/env bash
# Watchdog runner for Termux (also works fine on any Linux/VPS).
# Keeps the bot alive: if it crashes or the process dies, it restarts
# automatically after a short delay instead of the bot staying down.
#
# Usage inside Termux:
#   termux-wake-lock          # stop Android from freezing the process on sleep
#   chmod +x run.sh
#   tmux new -s bot           # keep it alive even if Termux app is closed
#   ./run.sh

cd "$(dirname "$0")" || exit 1

while true; do
    echo "[watchdog] $(date): starting bot..."
    python main.py
    EXIT_CODE=$?
    echo "[watchdog] $(date): bot exited with code $EXIT_CODE. Restarting in 5s..."
    sleep 5
done
