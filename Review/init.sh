#!/bin/bash
#"""
# Audiopro v0.3.1
# - Handles repository scaffolding for the canonical Audiopro file tree.
#"""

set -euo pipefail

echo "--- Audiopro v0.3.1: Canonical Tree Initializer ---"

# Canonical placement: init.sh at repo root.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "Repo root: $REPO_ROOT"

DIRS=(
  "core/analyzer"
  "core/brain/weights"
  "persistence"
  "services"
  "ui/components"
  "scripts"
  "database"
  "logs"
  "assets/icons"
  "tests/fixtures"
  "docs"
)

for d in "${DIRS[@]}"; do
  mkdir -p "$d"
done

create_if_missing() {
  local path="$1"
  local mode="${2:-}"
  if [ -f "$path" ]; then
    return 0
  fi
  echo "Creating: $path"
  mkdir -p "$(dirname "$path")"
  cat > "$path"
  if [ -n "$mode" ]; then
    chmod "$mode" "$path"
  fi
}

create_placeholder_py() {
  local path="$1"
  local use_case="$2"
  if [ -f "$path" ]; then
    return 0
  fi
  create_if_missing "$path" "" <<EOF
#"""
# Audiopro v0.3.1
# - Handles the ${use_case}.
#"""

# Planned / Deferred placeholder.
# Implement only when explicitly approved.

EOF
}

create_placeholder_md() {
  local path="$1"
  local title="$2"
  if [ -f "$path" ]; then
    return 0
  fi
  create_if_missing "$path" "" <<EOF
# ${title}

<!--
Audiopro v0.3.1
Planned / Deferred.
Create content only when explicitly approved.
-->

EOF
}

create_placeholder_qss() {
  local path="$1"
  if [ -f "$path" ]; then
    return 0
  fi
  create_if_missing "$path" "" <<EOF
/*"""
Audiopro v0.3.1
- Handles the Qt stylesheet theme (Planned / Deferred).
"""*/

/* Planned / Deferred placeholder. */

EOF
}

# Planned / Deferred artifacts (explicitly permitted by canonical structure)
create_placeholder_py "services/mock_llm.py" "LLM provider testing stub (Planned / Deferred)"
create_placeholder_qss "ui/theme.qss"
create_placeholder_py "tests/test_model.py" "ML inference tests (Planned / Deferred)"
create_placeholder_py "tests/test_llm_service.py" "LLM bridge tests (Planned / Deferred)"
create_placeholder_py "tests/test_repository.py" "Persistence tests (Planned / Deferred)"
create_placeholder_md "docs/RELEASE_NOTES.md" "Release Notes"
create_placeholder_md "docs/CERTIFICATION_REPORT.md" "Certification Report"

# Logs (do not overwrite)
create_if_missing "logs/analysis.log" ""
create_if_missing "logs/system.log" ""

# .gitignore (do not overwrite)
if [ ! -f ".gitignore" ]; then
  echo "Creating: .gitignore"
  cat > ".gitignore" <<'EOF'
#"""
# Audiopro v0.3.1
# - Handles git ignore rules for logs and local databases.
#"""

logs/
*.log

database/
*.db

__pycache__/
*.pyc
EOF
fi

echo "Canonical tree initialization complete."
