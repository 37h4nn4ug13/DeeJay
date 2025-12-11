#!/usr/bin/env bash
set -euo pipefail

TARGET=${TARGET:-"x86_64-unknown-linux-gnu"}
BIN_NAME=${BIN_NAME:-"deejay"}
DIST_DIR=${DIST_DIR:-"dist"}
OUTPUT_DIR="$DIST_DIR/$TARGET"

if [[ $# -gt 0 ]]; then
  TARGET="$1"
  OUTPUT_DIR="$DIST_DIR/$TARGET"
fi

BIN_PATH="target/$TARGET/release/$BIN_NAME"

if [[ ! -x "$BIN_PATH" ]]; then
  echo "Binary not found at $BIN_PATH. Build the release target first." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

cp "$BIN_PATH" "$OUTPUT_DIR/"
cp -r assets "$OUTPUT_DIR/"
cp -r runtime "$OUTPUT_DIR/"

cat > "$OUTPUT_DIR/BUILD_INFO" <<INFO
Target: $TARGET
Binary: $BIN_NAME
Bundled: $(date -u)
INFO

echo "Bundled artifacts into $OUTPUT_DIR"
