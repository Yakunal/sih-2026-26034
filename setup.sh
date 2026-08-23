#!/usr/bin/env bash
#
# setup.sh - get this project running on a machine that has never run it.
#
#   bash setup.sh
#
# Run it from the project root. It is safe to run more than once: every step
# checks whether it is already done and skips itself if so.
#
# WHY THIS SCRIPT EXISTS
# ----------------------
# The project folder can be copied between machines (Drive, USB, zip), but two
# directories inside it cannot: `.venv` records the absolute path of the Python
# that created it, and `frontend/node_modules` contains compiled binaries built
# for one operating system. Copied to another laptop, both are dead weight that
# fails in confusing ways. This script detects that and rebuilds them.

set -e

say()  { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
note() { printf '    %s\n' "$1"; }
die()  { printf '\n\033[1;31mSETUP FAILED: %s\033[0m\n\n' "$1" >&2; exit 1; }

cd "$(dirname "$0")"
ROOT="$(pwd)"
note "Project root: $ROOT"

# ---------------------------------------------------------------------------
# 1. Find a Python interpreter
# ---------------------------------------------------------------------------
say "Looking for Python"

PYTHON=""
for candidate in python3 python py; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" --version >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done

[ -n "$PYTHON" ] || die "No working Python found. Install Python 3.11 or newer from python.org, tick 'Add to PATH', then run this again."

PY_VERSION="$($PYTHON --version 2>&1)"
note "Found $PY_VERSION"

# The project was built on 3.14, but anything from 3.11 up is fine. Below that,
# some of the pinned wheels in requirements.txt do not exist.
$PYTHON -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
  || die "$PY_VERSION is too old. This project needs Python 3.11 or newer."

# On Windows a virtualenv puts its executables in Scripts/, everywhere else bin/.
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) VENV_BIN=".venv/Scripts" ;;
  *)                    VENV_BIN=".venv/bin" ;;
esac
VENV_PY="$ROOT/$VENV_BIN/python"
[ -x "$VENV_PY" ] || VENV_PY="$ROOT/$VENV_BIN/python.exe"

# ---------------------------------------------------------------------------
# 2. Virtual environment
# ---------------------------------------------------------------------------
say "Setting up the Python virtual environment"

# A .venv copied from another machine still contains its old absolute paths, so
# it either refuses to start or imports the wrong interpreter. Test it, and if
# it does not run, throw it away and build a fresh one.
if [ -d .venv ]; then
  if "$VENV_PY" --version >/dev/null 2>&1; then
    note "Existing .venv works, keeping it."
  else
    note "Existing .venv does not run here (it was built on another machine). Rebuilding."
    rm -rf .venv
  fi
fi

if [ ! -d .venv ]; then
  note "Creating .venv ..."
  $PYTHON -m venv .venv || die "Could not create the virtual environment."
  # Recompute: the interpreter name differs between Windows and everything else.
  VENV_PY="$ROOT/$VENV_BIN/python"
  [ -x "$VENV_PY" ] || VENV_PY="$ROOT/$VENV_BIN/python.exe"
fi

"$VENV_PY" --version >/dev/null 2>&1 || die "The virtual environment was created but its Python will not run."

say "Installing backend dependencies"
"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install -r requirements.txt || die "pip install failed. If it names one package with no matching wheel for $PY_VERSION, loosen that line in requirements.txt from '==' to '>=' and run this again."
note "Done."

# ---------------------------------------------------------------------------
# 3. Environment file
# ---------------------------------------------------------------------------
say "Checking the .env file"

if [ -f .env ]; then
  note ".env already exists, leaving it alone."
else
  cp .env.example .env
  note "Created .env from .env.example."
  note "It has no API key yet. Demo Mode works without one; live scanning does not."
fi

# ---------------------------------------------------------------------------
# 4. Frontend
# ---------------------------------------------------------------------------
say "Installing frontend dependencies"

command -v npm >/dev/null 2>&1 || die "npm not found. Install Node.js 20 or newer from nodejs.org, then run this again."
note "Found npm $(npm --version), node $(node --version)"

cd frontend
if [ -f package-lock.json ]; then
  # npm ci deletes node_modules first, which is exactly what we want if the
  # folder was copied from a different machine with the wrong native binaries.
  npm ci || die "npm ci failed in frontend/."
else
  npm install || die "npm install failed in frontend/."
fi
cd "$ROOT"
note "Done."

# ---------------------------------------------------------------------------
# 5. Demo images
# ---------------------------------------------------------------------------
say "Checking the demo label images"

if [ -f sample_data/demo_images/demo-1-compliant.png ]; then
  note "Already present."
else
  "$VENV_PY" sample_data/generate_demo_images.py || die "Could not generate the demo images."
fi

# ---------------------------------------------------------------------------
# 6. Database
# ---------------------------------------------------------------------------
say "Checking the inspection database"

if [ -f backend/compliance.db ]; then
  note "backend/compliance.db already exists, leaving its rows alone."
  note "To start clean with 20 fresh sample rows: $VENV_BIN/python backend/seed_data.py --reset"
else
  note "No database yet. Creating it and adding 20 sample inspections ..."
  "$VENV_PY" backend/seed_data.py || die "Could not seed the database."
fi

# ---------------------------------------------------------------------------
# 7. Prove the rule engine works before claiming success
# ---------------------------------------------------------------------------
say "Running the rule engine tests"
"$VENV_PY" backend/test_compliance.py || die "The rule engine tests failed. Do not demo until this passes."

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
cat <<EOF

$(printf '\033[1;32mSETUP COMPLETE\033[0m')

Start the backend (leave it running):

    cd backend && ../$VENV_BIN/python -m uvicorn main:app --reload --port 8000

Start the frontend in a second terminal:

    cd frontend && npm run dev

Then open http://localhost:5173

No API key is needed to demo: the four prepared products on the Scan page run
the real rule engine against cached label readings. Add GEMINI_API_KEY to .env
and restart the backend to enable live scanning of your own photographs.

EOF
