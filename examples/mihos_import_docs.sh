#!/usr/bin/env bash
# Import MIHOS shared docs as GoBP Document nodes (bash / Git Bash on Windows).
#
# Usage (from Git Bash):
#   cd /d/MIHOS-v1   # or: cd "D:/MIHOS-v1"
#   bash /d/GoBP/examples/mihos_import_docs.sh
#
# Requires: sha256sum OR openssl, sed, grep.
# Dry-run: MIHOS_IMPORT_DRY_RUN=1 bash mihos_import_docs.sh

set -euo pipefail

ROOT="${MIHOS_ROOT:-D:/MIHOS-v1}"
DOCS_DIR="$ROOT/mihos-shared/docs"
NODES_DIR="$ROOT/.gobp/nodes"

if [[ ! -d "$DOCS_DIR" ]]; then
  echo "ERROR: docs dir not found: $DOCS_DIR" >&2
  exit 1
fi

mkdir -p "$NODES_DIR"

now_iso() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

file_sha256() {
  local f="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$f" | awk '{print $1}'
  else
    openssl dgst -sha256 "$f" | awk '{print $NF}'
  fi
}

extract_title() {
  local f="$1"
  # YAML title: "Something" or title: Something
  if grep -q '^title:' "$f"; then
    sed -n 's/^title:[[:space:]]*//p' "$f" | head -1 | sed 's/^"//;s/"$//;s/^'"'"'//;s/'"'"'$//'
  else
    echo ""
  fi
}

for docfile in "$DOCS_DIR"/DOC-*.md; do
  [[ -e "$docfile" ]] || continue
  filename=$(basename "$docfile")
  base="${filename%.md}"

  # id: doc:DOC-01_soul (schema allows doc:.+)
  node_id="doc:${base}"
  safe_file="${node_id//:/_}.md"
  nodepath="$NODES_DIR/$safe_file"

  title=$(extract_title "$docfile")
  if [[ -z "${title// }" ]]; then
    title="$base"
  fi

  hash_hex=$(file_sha256 "$docfile")
  ts="$(now_iso)"

  # source_path: relative to project root (MIHOS-v1)
  rel="mihos-shared/docs/$filename"

  if [[ "${MIHOS_IMPORT_DRY_RUN:-0}" == "1" ]]; then
    echo "DRY-RUN would write: $nodepath  ($node_id)"
    continue
  fi

  cat > "$nodepath" << EOF
---
id: ${node_id}
type: Document
name: ${title}
source_path: ${rel}
content_hash: sha256:${hash_hex}
registered_at: '${ts}'
last_verified: '${ts}'
created: '${ts}'
updated: '${ts}'
status: ACTIVE
sections: []
---

# ${title}

Source file: [\`${filename}\`](../../${rel})
EOF

  echo "Created: $nodepath"
done

echo "Done. Reload graph (or restart MCP) and run validate: metadata if needed."
