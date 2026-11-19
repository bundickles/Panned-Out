#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/panned-out"
key_file="$config_dir/groq-api-key"
if [[ -z "${GROQ_API_KEY:-}" && -f "$key_file" ]]; then
    IFS= read -r GROQ_API_KEY < "$key_file" || true
fi
if [[ -z "${GROQ_API_KEY:-}" ]]; then
    read -rsp 'Paste your GroqCloud API key (hidden): ' GROQ_API_KEY
    printf '\n'
    if [[ -z "$GROQ_API_KEY" ]]; then
        printf 'A GroqCloud API key is required. Create one at https://console.groq.com/keys.\n' >&2
        exit 1
    fi
    mkdir -p "$config_dir"
    chmod 700 "$config_dir"
    printf '%s\n' "$GROQ_API_KEY" > "$key_file"
    chmod 600 "$key_file"
    printf 'Saved the Groq key in your private local configuration. Future starts load it automatically.\n'
fi
export GROQ_API_KEY
javac --release 11 -d backend/build backend/src/*.java
exec java -cp backend/build RecipeServer "${1:-8081}"
