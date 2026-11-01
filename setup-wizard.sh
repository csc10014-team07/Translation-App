#!/usr/bin/env bash
# Forwarder for canonical scripts/setup-wizard.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/scripts/setup-wizard.sh" "$@"
