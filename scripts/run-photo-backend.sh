#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -z "${GEMINI_API_KEY:-}" ]]; then
    read -rsp 'Paste your Gemini API key (hidden): ' GEMINI_API_KEY
    printf '\n'
    export GEMINI_API_KEY
fi
if [[ -z "$GEMINI_API_KEY" ]]; then
    printf 'A Gemini API key is required. Create one in Google AI Studio.\n' >&2
    exit 1
fi
javac --release 11 -d backend/build backend/src/*.java
exec java -Djava.awt.headless=true -cp backend/build RecipeServer "${1:-8082}"
