#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

# The Anthropic/Runway/ElevenLabs SDKs currently crash on Python 3.14 with:
#   'typing.Union' object has no attribute '__discriminator__'
# (3.14 made typing.Union immutable; the SDKs' generated code hasn't caught up).
# Prefer 3.13/3.12/3.11 if available.
PYBIN=""
for v in 3.13 3.12 3.11; do
  if command -v "python$v" >/dev/null 2>&1; then
    PYBIN="python$v"
    break
  fi
done

if [ -z "$PYBIN" ]; then
  PYBIN="python3"
  ver=$($PYBIN --version 2>&1 | awk '{print $2}')
  case "$ver" in
    3.14*)
      echo
      echo "WARNING: Only Python 3.14 ($ver) was found."
      echo "This project's SDKs currently crash on 3.14 with a typing.Union error."
      echo "Install Python 3.12 or 3.13 (e.g. via pyenv or your package manager)."
      echo "Continuing with 3.14 anyway - film generation will likely fail."
      echo
      ;;
  esac
fi

echo "Using interpreter: $PYBIN ($($PYBIN --version))"
$PYBIN -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -q -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
