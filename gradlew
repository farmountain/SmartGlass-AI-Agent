#!/usr/bin/env sh
set -e
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
GRADLE_EXEC=""
if [ -n "$GRADLE_HOME" ] && [ -x "$GRADLE_HOME/bin/gradle" ]; then
  GRADLE_EXEC="$GRADLE_HOME/bin/gradle"
elif command -v gradle >/dev/null 2>&1; then
  GRADLE_EXEC="$(command -v gradle)"
else
  echo "Gradle is required to run this project. Please install Gradle or set GRADLE_HOME." >&2
  exit 1
fi
exec "$GRADLE_EXEC" "$@"
