---
name: Python package installation
description: Replit package installation behavior for this bot workspace.
---

For the Python bot, the package installation helper succeeded with unpinned package names after a pinned-version request failed.

**Why:** The workspace package firewall/runtime resolver may reject a fully pinned install even when the same compatible dependencies are available.

**How to apply:** If dependency installation fails with exact pins, retry the same direct dependencies unpinned before changing the project requirements file or replacing libraries.